export const ASSISTANT_MESSAGE_MAX_LENGTH = 12000

export type AssistantRole = 'user' | 'assistant'

export type AssistantRequestStatus = 'idle' | 'processing' | 'failed'

export type InvestigationStatus = 'idle' | 'processing' | 'failed' | 'ready'

export type RelatedMatchStrength = 'strong' | 'moderate'

export type RootCauseCategory =
  | 'material'
  | 'equipment'
  | 'method'
  | 'people'
  | 'measurement'
  | 'environment'
  | 'other'

export type CapaSuggestionType =
  | 'immediate_correction'
  | 'corrective_action'
  | 'preventive_action'
  | 'effectiveness_check'

export interface RelatedComplaintMatch {
  complaint_id: string
  complaint_number: string
  score: number
  match_strength: RelatedMatchStrength
  reasons: string[]
  product_name: string
  batch_lot_number: string
  customer_name: string
  complaint_category: string
  complaint_description: string
  committed_at: string
}

export interface RootCauseHypothesis {
  category: RootCauseCategory
  hypothesis: string
  rationale: string
  supporting_fields: string[]
  evidence_needed: string[]
}

export interface CapaSuggestion {
  type: CapaSuggestionType
  action: string
  rationale: string
}

export interface InvestigationAssistance {
  complaint_summary: string
  root_cause_hypotheses: RootCauseHypothesis[]
  capa_suggestions: CapaSuggestion[]
  related_history_used: boolean
}

export interface AssistantMessage {
  id: string
  role: AssistantRole
  content: string
}

export interface AssistantState {
  messages: AssistantMessage[]
  requestStatus: AssistantRequestStatus
  error: string | null
  statusBeforeProcessing:
    | 'pending_triage'
    | 'processing'
    | 'needs_information'
    | 'ready_to_commit'
    | 'committed'
    | null
  relatedComplaints: RelatedComplaintMatch[]
  relatedLookupEvaluated: boolean
  investigationStatus: InvestigationStatus
  investigationError: string | null
  investigationAssistance: InvestigationAssistance | null
}

export function createInitialAssistantState(): AssistantState {
  return {
    messages: [],
    requestStatus: 'idle',
    error: null,
    statusBeforeProcessing: null,
    relatedComplaints: [],
    relatedLookupEvaluated: false,
    investigationStatus: 'idle',
    investigationError: null,
    investigationAssistance: null,
  }
}

export function createAssistantMessageId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function formatMatchStrength(strength: RelatedMatchStrength): string {
  return strength === 'strong' ? 'Strong match' : 'Moderate match'
}

export function formatSimilarityPercent(score: number): string {
  return `${Math.round(score * 100)}%`
}

export const ROOT_CAUSE_CATEGORY_LABELS: Record<RootCauseCategory, string> = {
  material: 'Material',
  equipment: 'Equipment',
  method: 'Method / Process',
  people: 'People',
  measurement: 'Measurement',
  environment: 'Environment',
  other: 'Other',
}

export const CAPA_TYPE_LABELS: Record<CapaSuggestionType, string> = {
  immediate_correction: 'Immediate Correction',
  corrective_action: 'Corrective Action',
  preventive_action: 'Preventive Action',
  effectiveness_check: 'Effectiveness Check',
}

export const CAPA_TYPE_ORDER: CapaSuggestionType[] = [
  'immediate_correction',
  'corrective_action',
  'preventive_action',
  'effectiveness_check',
]
