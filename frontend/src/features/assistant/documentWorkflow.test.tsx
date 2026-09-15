import { configureStore } from '@reduxjs/toolkit'
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import { Provider } from 'react-redux'
import { afterEach, describe, expect, it, vi } from 'vitest'

import assistantReducer from './assistantSlice'
import complaintReducer from '../complaint/complaintSlice'
import {
  createInitialComplaintDraftState,
  type ComplaintDraftState,
  type ComplaintFieldValue,
} from '../complaint/complaintTypes'
import { ComplaintWorkspace } from '../complaint/components/ComplaintWorkspace'
import { MAX_UPLOAD_BYTES } from './documentLimits'

function field(
  value: string,
  provenance: ComplaintFieldValue['provenance'] = 'source',
): ComplaintFieldValue {
  return {
    value,
    provenance,
    confidence: null,
    evidence: provenance === 'source' ? value : null,
  }
}

function populatedState(): ComplaintDraftState {
  const state = createInitialComplaintDraftState()
  state.fields.product_name = field('Amoxicillin Capsules')
  state.fields.batch_lot_number = field('AMX240602')
  state.fields.customer_name = field('Apollo Pharmacy')
  state.fields.complaint_description = field('Discolored capsules.')
  state.status = 'needs_information'
  return state
}

function createStore(preloaded?: ComplaintDraftState) {
  return configureStore({
    reducer: { complaint: complaintReducer, assistant: assistantReducer },
    preloadedState: preloaded ? { complaint: preloaded } : undefined,
  })
}

function renderWorkspace(preloaded?: ComplaintDraftState) {
  const store = createStore(preloaded)
  render(
    <Provider store={store}>
      <ComplaintWorkspace />
    </Provider>,
  )
  return store
}

function makeFile(
  name: string,
  contents: string,
  type = 'application/pdf',
  size?: number,
): File {
  const file = new File([contents], name, { type })
  if (typeof size === 'number') {
    Object.defineProperty(file, 'size', { value: size })
  }
  return file
}

const DOCUMENT_SUCCESS = {
  intent: 'new_complaint',
  patch: {
    changes: {
      customer_name: {
        value: 'Northstar Pharma Distribution',
        provenance: 'source',
        confidence: null,
        evidence: 'Northstar Pharma Distribution',
      },
      product_name: {
        value: 'Cefixime Capsules 200 mg',
        provenance: 'source',
        confidence: null,
        evidence: 'Cefixime Capsules 200 mg',
      },
      batch_lot_number: {
        value: 'CFX260481',
        provenance: 'source',
        confidence: null,
        evidence: 'CFX260481',
      },
      complaint_source: {
        value: 'Email',
        provenance: 'source',
        confidence: null,
        evidence: 'Email',
      },
      complaint_description: {
        value: 'Brown discoloration observed.',
        provenance: 'source',
        confidence: null,
        evidence: null,
      },
      complaint_category: {
        value: 'Appearance / discoloration',
        provenance: 'inferred',
        confidence: null,
        evidence: null,
      },
      initial_risk_assessment: {
        value: 'Investigate discoloration before further distribution.',
        provenance: 'inferred',
        confidence: null,
        evidence: null,
      },
    },
  },
  status: 'ready_to_commit',
  missing_required_fields: [],
  assistant_message:
    'I extracted the complaint document and prepared an initial risk assessment. The record is ready for QA review.',
  warnings: [],
  document: { filename: 'complaint-report.pdf', document_type: 'pdf' },
}

describe('Assistant document workflow', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('enables the upload area', () => {
    renderWorkspace()
    expect(screen.getByText('Upload complaint document')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Choose file' })).toBeEnabled()
    expect(screen.getByText(/Supported: PDF · TXT · EML/)).toBeInTheDocument()
  })

  it('selects a supported file and displays its name', () => {
    renderWorkspace()
    const input = document.getElementById(
      'assistant-document-input',
    ) as HTMLInputElement
    const file = makeFile('complaint-report.pdf', '%PDF-1.4 sample')
    fireEvent.change(input, { target: { files: [file] } })
    expect(screen.getByText('complaint-report.pdf')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Analyze Document' })).toBeEnabled()
  })

  it('rejects an unsupported extension on the client', () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    renderWorkspace()
    const input = document.getElementById(
      'assistant-document-input',
    ) as HTMLInputElement
    fireEvent.change(input, {
      target: { files: [makeFile('notes.docx', 'docx-bytes', 'application/vnd')] },
    })
    expect(
      screen.getByText(/Unsupported document type/),
    ).toBeInTheDocument()
    expect(screen.queryByText('notes.docx')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Analyze Document' })).toBeDisabled()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('rejects an oversized file before submission', () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    renderWorkspace()
    const input = document.getElementById(
      'assistant-document-input',
    ) as HTMLInputElement
    const file = makeFile(
      'huge.pdf',
      'x',
      'application/pdf',
      MAX_UPLOAD_BYTES + 1,
    )
    fireEvent.change(input, { target: { files: [file] } })
    expect(
      screen.getByText(/maximum upload size of 8 MB/),
    ).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('sends multipart FormData with file and current_fields', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => DOCUMENT_SUCCESS,
    })
    vi.stubGlobal('fetch', fetchMock)
    renderWorkspace()
    const input = document.getElementById(
      'assistant-document-input',
    ) as HTMLInputElement
    const file = makeFile('complaint-report.pdf', '%PDF-1.4 sample')
    fireEvent.change(input, { target: { files: [file] } })

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Analyze Document' }))
    })

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/assistant/process-document')
    expect(init.method).toBe('POST')
    expect(init.headers).toBeUndefined()
    expect(init.body).toBeInstanceOf(FormData)
    const formData = init.body as FormData
    expect(formData.get('file')).toBeInstanceOf(File)
    expect(formData.get('current_fields')).toEqual(expect.any(String))
    const fieldsJson = JSON.parse(String(formData.get('current_fields')))
    expect(fieldsJson.product_name.value).toBeNull()
  })

  it('applies a successful document patch and clears the selected file', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => DOCUMENT_SUCCESS,
      }),
    )
    const store = renderWorkspace()
    const input = document.getElementById(
      'assistant-document-input',
    ) as HTMLInputElement
    fireEvent.change(input, {
      target: {
        files: [makeFile('complaint-report.pdf', '%PDF-1.4 sample')],
      },
    })

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Analyze Document' }))
    })

    await waitFor(() => {
      expect(store.getState().complaint.fields.product_name.value).toBe(
        'Cefixime Capsules 200 mg',
      )
    })
    expect(store.getState().complaint.status).toBe('ready_to_commit')
    expect(
      screen.getByText(/Uploaded complaint document: complaint-report.pdf/),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/extracted the complaint document/),
    ).toBeInTheDocument()
    expect(screen.queryByText('complaint-report.pdf')).not.toBeInTheDocument()
    expect(store.getState().complaint.fields.product_name.provenance).toBe(
      'source',
    )
    expect(
      store.getState().complaint.fields.complaint_category.provenance,
    ).toBe('inferred')
    expect(
      screen.getByRole('button', { name: 'Commit Complaint' }),
    ).toBeEnabled()
  })

  it('preserves the draft and selected file when document processing fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        json: async () => ({
          detail:
            'This PDF does not contain readable embedded text. Scanned-image OCR is not enabled in this assessment build.',
        }),
      }),
    )
    const store = renderWorkspace()
    const input = document.getElementById(
      'assistant-document-input',
    ) as HTMLInputElement
    fireEvent.change(input, {
      target: { files: [makeFile('scan.pdf', '%PDF-1.4')] },
    })

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Analyze Document' }))
    })

    await waitFor(() => {
      expect(store.getState().assistant.requestStatus).toBe('failed')
    })
    expect(store.getState().complaint.fields.product_name.value).toBeNull()
    expect(store.getState().complaint.status).toBe('pending_triage')
    expect(screen.getByText('scan.pdf')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(/Scanned-image OCR is not enabled/)
    expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument()
  })

  it('switches the narrow layout to Complaint after successful document extraction', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => DOCUMENT_SUCCESS,
      }),
    )
    renderWorkspace()
    expect(
      screen.getByRole('tab', { name: 'Assistant' }),
    ).toHaveAttribute('aria-selected', 'true')

    const input = document.getElementById(
      'assistant-document-input',
    ) as HTMLInputElement
    fireEvent.change(input, {
      target: {
        files: [makeFile('complaint-report.pdf', '%PDF-1.4 sample')],
      },
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Analyze Document' }))
    })

    await waitFor(() => {
      expect(
        screen.getByRole('tab', { name: 'Complaint' }),
      ).toHaveAttribute('aria-selected', 'true')
    })
    const complaintPanel = document.getElementById('panel-complaint')
    expect(complaintPanel?.className).toContain('paneActive')
  })
})

describe('text workflows remain intact with document UI', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('still processes text complaints', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          ...DOCUMENT_SUCCESS,
          assistant_message:
            'I extracted the available complaint details. I still need: Complaint Source before this record can be ready for review.',
          status: 'needs_information',
          missing_required_fields: ['complaint_source'],
          document: null,
        }),
      }),
    )
    const store = renderWorkspace()
    fireEvent.change(screen.getByLabelText('Complaint input'), {
      target: { value: 'NovaCare Pharmacy reported brown discoloration.' },
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    })
    await waitFor(() => {
      expect(store.getState().complaint.fields.product_name.value).toBe(
        'Cefixime Capsules 200 mg',
      )
    })
  })

  it('still processes conversational corrections', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          intent: 'correction',
          patch: {
            changes: {
              batch_lot_number: {
                value: 'BMX240602',
                provenance: 'user',
                confidence: null,
                evidence: null,
              },
            },
          },
          status: 'needs_information',
          missing_required_fields: ['complaint_category'],
          assistant_message: 'Updated Batch / Lot Number.',
          warnings: [],
        }),
      }),
    )
    const store = renderWorkspace(populatedState())
    fireEvent.click(screen.getByRole('tab', { name: 'Assistant' }))
    fireEvent.change(screen.getByLabelText('Complaint input'), {
      target: { value: 'The batch is BMX240602.' },
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    })
    await waitFor(() => {
      expect(store.getState().complaint.fields.batch_lot_number.value).toBe(
        'BMX240602',
      )
    })
    expect(store.getState().complaint.fields.product_name.value).toBe(
      'Amoxicillin Capsules',
    )
    const assistantTab = screen.getByRole('tab', { name: 'Assistant' })
    expect(within(assistantTab).getByText('Assistant')).toBeInTheDocument()
  })
})
