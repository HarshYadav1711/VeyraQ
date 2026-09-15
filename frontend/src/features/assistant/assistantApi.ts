import type { ComplaintFields, ComplaintPatch, ComplaintStatus } from '../complaint/complaintTypes'

export interface AssistantProcessRequest {
  message: string
  fields: ComplaintFields
}

export interface AssistantProcessResponse {
  intent: 'new_complaint' | 'correction'
  patch: ComplaintPatch
  status: Extract<ComplaintStatus, 'needs_information' | 'ready_to_commit'>
  missing_required_fields: string[]
  assistant_message: string
  warnings: string[]
}

function apiBaseUrl(): string {
  const base = import.meta.env.VITE_API_BASE_URL
  if (typeof base !== 'string' || base.trim() === '') {
    throw new Error('VITE_API_BASE_URL is not configured')
  }
  return base.replace(/\/$/, '')
}

export class AssistantApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'AssistantApiError'
    this.status = status
  }
}

const FALLBACK_UNAVAILABLE =
  'AI processing is temporarily unavailable. Your complaint draft has not been changed.'

export async function postAssistantProcess(
  body: AssistantProcessRequest,
): Promise<AssistantProcessResponse> {
  const response = await fetch(`${apiBaseUrl()}/assistant/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    let message = FALLBACK_UNAVAILABLE
    try {
      const payload = (await response.json()) as {
        detail?: string | { detail?: string }
      }
      if (typeof payload.detail === 'string' && payload.detail.trim()) {
        message = payload.detail
      } else if (
        payload.detail &&
        typeof payload.detail === 'object' &&
        payload.detail.detail
      ) {
        message = payload.detail.detail
      }
    } catch {
      // Keep the safe default message.
    }
    if (response.status >= 500) {
      message = FALLBACK_UNAVAILABLE
    }
    throw new AssistantApiError(message, response.status)
  }

  return (await response.json()) as AssistantProcessResponse
}
