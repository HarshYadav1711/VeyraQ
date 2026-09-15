export const ASSISTANT_MESSAGE_MAX_LENGTH = 12000

export type AssistantRole = 'user' | 'assistant'

export type AssistantRequestStatus = 'idle' | 'processing' | 'failed'

export interface AssistantMessage {
  id: string
  role: AssistantRole
  content: string
}

export interface AssistantState {
  messages: AssistantMessage[]
  requestStatus: AssistantRequestStatus
  error: string | null
  statusBeforeProcessing: 'pending_triage' | 'processing' | 'needs_information' | 'ready_to_commit' | 'committed' | null
}

export function createInitialAssistantState(): AssistantState {
  return {
    messages: [],
    requestStatus: 'idle',
    error: null,
    statusBeforeProcessing: null,
  }
}

export function createAssistantMessageId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`
}
