import { expect, test, type Page } from '@playwright/test'

function sourceField(value: string, evidence = value) {
  return {
    value,
    provenance: 'source',
    confidence: null,
    evidence,
  }
}

function inferredField(value: string) {
  return {
    value,
    provenance: 'inferred',
    confidence: null,
    evidence: null,
  }
}

function userField(value: string) {
  return {
    value,
    provenance: 'user',
    confidence: null,
    evidence: null,
  }
}

function missingField() {
  return {
    value: null,
    provenance: 'missing',
    confidence: null,
    evidence: null,
  }
}

const INTAKE_FIELDS = {
  complaint_source: sourceField('Email'),
  customer_name: sourceField('NovaCare Pharmacy'),
  product_name: sourceField('Cefixime Capsules 200 mg'),
  product_strength_grade: sourceField('200 mg'),
  batch_lot_number: sourceField('CFX260481'),
  affected_quantity: sourceField('24 capsules'),
  manufacturing_date: sourceField('April 2026'),
  expiry_date: sourceField('March 2028'),
  complaint_date: missingField(),
  complaint_category: inferredField('Product Defect – Discoloration'),
  complaint_description: {
    value:
      'NovaCare Pharmacy reported brown discoloration on Cefixime Capsules 200 mg from batch CFX260481.',
    provenance: 'source',
    confidence: null,
    evidence: null,
  },
  originating_site_block: missingField(),
  impacted_non_product_materials: missingField(),
  initial_severity: inferredField('Major'),
  priority: inferredField('High'),
  suggested_next_action: inferredField(
    'Quarantine remaining stock and investigate the batch.',
  ),
  initial_risk_assessment: inferredField(
    'Appearance defect on a finished dosage form; investigate before further distribution.',
  ),
}

const INTAKE_RESPONSE = {
  intent: 'new_complaint',
  patch: {
    changes: { ...INTAKE_FIELDS },
  },
  status: 'ready_to_commit',
  missing_required_fields: [],
  assistant_message:
    'I extracted the complaint and prepared an initial risk assessment. The record is ready for QA review.',
  warnings: [],
  related_complaints: [],
  related_lookup_evaluated: true,
}

const CORRECTION_RESPONSE = {
  intent: 'correction',
  patch: {
    changes: {
      batch_lot_number: userField('BMX240602'),
      affected_quantity: userField('48 capsules'),
      initial_severity: inferredField('Major'),
      priority: inferredField('High'),
      suggested_next_action: inferredField(
        'Quarantine remaining stock and investigate the corrected batch.',
      ),
      initial_risk_assessment: inferredField(
        'Appearance defect on a finished dosage form; investigate before further distribution.',
      ),
    },
  },
  status: 'ready_to_commit',
  missing_required_fields: [],
  assistant_message: 'Updated Batch / Lot Number and Affected Quantity.',
  warnings: [],
  related_complaints: [],
  related_lookup_evaluated: true,
}

const DOCUMENT_RESPONSE = {
  ...INTAKE_RESPONSE,
  assistant_message:
    'I extracted the available complaint details from the document. The record is ready for QA review.',
  document: {
    filename: 'complaint-report.pdf',
    document_type: 'pdf',
  },
  patch: {
    changes: {
      ...INTAKE_FIELDS,
      customer_name: sourceField('Northstar Formulations'),
      product_name: sourceField('Metformin Hydrochloride API'),
      product_strength_grade: sourceField('IP/BP'),
      batch_lot_number: sourceField('MFH260712A'),
      affected_quantity: sourceField('25 kg (1 HDPE drum)'),
      complaint_description: {
        value:
          'Dark foreign particulate observed during incoming inspection of Metformin Hydrochloride API.',
        provenance: 'source',
        confidence: null,
        evidence: null,
      },
    },
  },
}

async function mockAssistantApis(page: Page) {
  await page.route('**/api/v1/assistant/process', async (route) => {
    const body = route.request().postDataJSON() as { message?: string }
    const message = body.message ?? ''
    const payload = message.toLowerCase().includes('correction')
      ? CORRECTION_RESPONSE
      : INTAKE_RESPONSE
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(payload),
    })
  })

  await page.route('**/api/v1/assistant/process-document', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(DOCUMENT_RESPONSE),
    })
  })

  await page.route('**/api/v1/complaints/commit', async (route) => {
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: '11111111-1111-4111-8111-111111111199',
        complaint_number: 'CMP-2026-E2E01',
        status: 'committed',
        fields: {
          ...INTAKE_FIELDS,
        },
        created_at: '2026-03-17T12:00:00Z',
        committed_at: '2026-03-17T12:00:00Z',
      }),
    })
  })
}

test.describe('Critical product journeys', () => {
  test('text complaint → Ready to Commit → Commit', async ({ page }) => {
    await mockAssistantApis(page)
    await page.goto('/')

    await page.getByLabel('Complaint input').fill(
      'NovaCare Pharmacy reported brown discoloration on Cefixime Capsules 200 mg from batch CFX260481.',
    )
    await page.getByRole('button', { name: 'Send' }).click()

    await expect(page.getByLabel('Product Name')).toHaveValue(
      'Cefixime Capsules 200 mg',
    )
    await expect(page.getByLabel('Batch / Lot Number')).toHaveValue('CFX260481')
    await expect(
      page.getByRole('button', { name: 'Commit Complaint' }),
    ).toBeEnabled()

    await page.getByRole('button', { name: 'Commit Complaint' }).click()
    await expect(page.getByText('CMP-2026-E2E01')).toBeVisible()
  })

  test('correction updates only corrected fields', async ({ page }) => {
    await mockAssistantApis(page)
    await page.goto('/')

    await page.getByLabel('Complaint input').fill(
      'NovaCare Pharmacy reported brown discoloration on Cefixime Capsules 200 mg from batch CFX260481.',
    )
    await page.getByRole('button', { name: 'Send' }).click()
    await expect(page.getByLabel('Product Name')).toHaveValue(
      'Cefixime Capsules 200 mg',
    )

    const productBefore = await page.getByLabel('Product Name').inputValue()
    const customerBefore = await page.getByLabel('Customer Name').inputValue()

    await page.getByLabel('Complaint input').fill(
      'Correction: the batch is BMX240602 and 48 capsules were affected.',
    )
    await page.getByRole('button', { name: 'Send' }).click()

    await expect(page.getByLabel('Batch / Lot Number')).toHaveValue('BMX240602')
    await expect(page.getByLabel('Affected Quantity')).toHaveValue('48 capsules')
    await expect(page.getByLabel('Product Name')).toHaveValue(productBefore)
    await expect(page.getByLabel('Customer Name')).toHaveValue(customerBefore)
  })

  test('document upload populates complaint for review', async ({ page }) => {
    await mockAssistantApis(page)
    await page.goto('/')

    await page.setInputFiles('#assistant-document-input', {
      name: 'complaint-report.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 fictional demo bytes'),
    })
    await page.getByRole('button', { name: 'Analyze Document' }).click()

    await expect(page.getByLabel('Customer Name')).toHaveValue(
      'Northstar Formulations',
    )
    await expect(page.getByLabel('Product Name')).toHaveValue(
      'Metformin Hydrochloride API',
    )
    await expect(page.getByLabel('Batch / Lot Number')).toHaveValue('MFH260712A')
    await expect(
      page.getByRole('status', { name: /Complaint status:/ }),
    ).toBeVisible()
  })
})
