import {
  COMPLAINT_FIELD_KEYS,
  type ComplaintFieldKey,
  type ComplaintFields,
  type ComplaintStatus,
  type FieldProvenance,
} from './complaintTypes'

export type FieldControlType = 'input' | 'textarea'

export interface ComplaintFieldDisplayConfig {
  key: ComplaintFieldKey
  label: string
  control: FieldControlType
  placeholder?: string
}

export interface ComplaintSectionConfig {
  id: string
  title: string
  fields: readonly ComplaintFieldDisplayConfig[]
}

export const COMPLAINT_STATUS_LABELS: Record<ComplaintStatus, string> = {
  pending_triage: 'Pending Triage',
  processing: 'Processing',
  needs_information: 'Needs Information',
  ready_to_commit: 'Ready to Commit',
  committed: 'Committed',
}

export const PROVENANCE_LABELS: Record<FieldProvenance, string> = {
  source: 'Extracted',
  user: 'User edited',
  inferred: 'AI suggestion · Verify',
  missing: 'Not provided',
}

export const COMPLAINT_SECTIONS: readonly ComplaintSectionConfig[] = [
  {
    id: 'origin-customer',
    title: 'Origin & Customer Details',
    fields: [
      {
        key: 'complaint_source',
        label: 'Complaint Source',
        control: 'input',
        placeholder: 'e.g. Email, phone, document',
      },
      {
        key: 'customer_name',
        label: 'Customer Name',
        control: 'input',
        placeholder: 'e.g. customer or organization name',
      },
    ],
  },
  {
    id: 'product-batch',
    title: 'Product & Batch Identification',
    fields: [
      {
        key: 'product_name',
        label: 'Product Name',
        control: 'input',
        placeholder: 'e.g. product or material name',
      },
      {
        key: 'product_strength_grade',
        label: 'Product Strength / Grade',
        control: 'input',
        placeholder: 'e.g. 500 mg',
      },
      {
        key: 'batch_lot_number',
        label: 'Batch / Lot Number',
        control: 'input',
        placeholder: 'e.g. BMX240602',
      },
      {
        key: 'affected_quantity',
        label: 'Affected Quantity',
        control: 'input',
        placeholder: 'e.g. 48 capsules',
      },
      {
        key: 'manufacturing_date',
        label: 'Manufacturing Date',
        control: 'input',
        placeholder: 'e.g. March 2026',
      },
      {
        key: 'expiry_date',
        label: 'Expiry Date',
        control: 'input',
        placeholder: 'e.g. February 2028',
      },
    ],
  },
  {
    id: 'complaint-details',
    title: 'Complaint Details',
    fields: [
      {
        key: 'complaint_date',
        label: 'Complaint Date',
        control: 'input',
        placeholder: 'e.g. 12 March 2026',
      },
      {
        key: 'complaint_category',
        label: 'Complaint Type / Category',
        control: 'input',
        placeholder: 'e.g. packaging defect',
      },
      {
        key: 'complaint_description',
        label: 'Complaint Description',
        control: 'textarea',
        placeholder: 'Describe the customer complaint',
      },
    ],
  },
  {
    id: 'facility-material',
    title: 'Facility & Material Impact',
    fields: [
      {
        key: 'originating_site_block',
        label: 'Originating Site Block',
        control: 'input',
        placeholder: 'e.g. Site / block identifier',
      },
      {
        key: 'impacted_non_product_materials',
        label: 'Impacted Non-Product Materials',
        control: 'input',
        placeholder: 'e.g. packaging components',
      },
    ],
  },
  {
    id: 'initial-assessment',
    title: 'Initial Assessment',
    fields: [
      {
        key: 'initial_severity',
        label: 'Initial Severity',
        control: 'input',
        placeholder: 'e.g. Medium',
      },
      {
        key: 'priority',
        label: 'Priority',
        control: 'input',
        placeholder: 'e.g. High',
      },
      {
        key: 'suggested_next_action',
        label: 'Suggested Next Action',
        control: 'textarea',
        placeholder: 'Advisory next step for QA review',
      },
      {
        key: 'initial_risk_assessment',
        label: 'Initial Risk Assessment',
        control: 'textarea',
        placeholder: 'Advisory risk assessment',
      },
    ],
  },
]

export function isComplaintEmpty(fields: ComplaintFields): boolean {
  return COMPLAINT_FIELD_KEYS.every((key) => fields[key].value === null)
}

const FIELD_LABEL_LOOKUP: Partial<Record<ComplaintFieldKey, string>> = Object.fromEntries(
  COMPLAINT_SECTIONS.flatMap((section) =>
    section.fields.map((field) => [field.key, field.label] as const),
  ),
)

export function complaintFieldLabel(key: string): string {
  return FIELD_LABEL_LOOKUP[key as ComplaintFieldKey] ?? key
}
