export const COMPLAINT_FIELD_KEYS = [
  'complaint_source',
  'customer_name',
  'product_name',
  'product_strength_grade',
  'batch_lot_number',
  'affected_quantity',
  'manufacturing_date',
  'expiry_date',
  'complaint_date',
  'complaint_category',
  'complaint_description',
  'originating_site_block',
  'impacted_non_product_materials',
  'initial_severity',
  'priority',
  'suggested_next_action',
  'initial_risk_assessment',
] as const

export type ComplaintFieldKey = (typeof COMPLAINT_FIELD_KEYS)[number]

export type FieldProvenance = 'source' | 'user' | 'inferred' | 'missing'

export type ComplaintStatus =
  | 'pending_triage'
  | 'processing'
  | 'needs_information'
  | 'ready_to_commit'
  | 'committed'

export interface ComplaintFieldValue {
  value: string | null
  provenance: FieldProvenance
  confidence: number | null
  evidence: string | null
}

export type ComplaintFields = Record<ComplaintFieldKey, ComplaintFieldValue>

export interface ComplaintPatch {
  changes: Partial<Record<ComplaintFieldKey, ComplaintFieldValue>>
}

export interface ComplaintDraftState {
  fields: ComplaintFields
  status: ComplaintStatus
  recentlyUpdatedFields: ComplaintFieldKey[]
}

export function createEmptyComplaintFieldValue(): ComplaintFieldValue {
  return {
    value: null,
    provenance: 'missing',
    confidence: null,
    evidence: null,
  }
}

export function createEmptyComplaintFields(): ComplaintFields {
  const fields = {} as ComplaintFields
  for (const key of COMPLAINT_FIELD_KEYS) {
    fields[key] = createEmptyComplaintFieldValue()
  }
  return fields
}

export function createInitialComplaintDraftState(): ComplaintDraftState {
  return {
    fields: createEmptyComplaintFields(),
    status: 'pending_triage',
    recentlyUpdatedFields: [],
  }
}
