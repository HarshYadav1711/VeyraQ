import type { ComplaintFields, ComplaintPatch, ComplaintStatus } from '../complaint/complaintTypes'

export interface AssistantProcessRequest {
  message: string
  fields: ComplaintFields
}

export interface DocumentMetadata {
  filename: string
  document_type: 'pdf' | 'txt' | 'eml'
}

export interface AssistantProcessResponse {
  intent: 'new_complaint' | 'correction'
  patch: ComplaintPatch
  status: Extract<ComplaintStatus, 'needs_information' | 'ready_to_commit'>
  missing_required_fields: string[]
  assistant_message: string
  warnings: string[]
  document?: DocumentMetadata | null
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

function detailFromPayload(payload: unknown): string | null {
  if (!payload || typeof payload !== 'object') {
    return null
  }
  const detail = (payload as { detail?: unknown }).detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  if (detail && typeof detail === 'object' && 'detail' in detail) {
    const nested = (detail as { detail?: unknown }).detail
    if (typeof nested === 'string' && nested.trim()) {
      return nested
    }
  }
  return null
}

async function raiseForErrorResponse(response: Response): Promise<never> {
  let message = FALLBACK_UNAVAILABLE
  try {
    const payload: unknown = await response.json()
    const detail = detailFromPayload(payload)
    if (detail) {
      message = detail
    }
  } catch {
    // Keep the safe default message.
  }
  if (response.status >= 500) {
    message = FALLBACK_UNAVAILABLE
  }
  throw new AssistantApiError(message, response.status)
}

export async function postAssistantProcess(
  body: AssistantProcessRequest,
): Promise<AssistantProcessResponse> {
  const response = await fetch(`${apiBaseUrl()}/assistant/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    await raiseForErrorResponse(response)
  }

  return (await response.json()) as AssistantProcessResponse
}

export async function processComplaintDocument(
  file: File,
  fields: ComplaintFields,
): Promise<AssistantProcessResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('current_fields', JSON.stringify(fields))

  const response = await fetch(`${apiBaseUrl()}/assistant/process-document`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    await raiseForErrorResponse(response)
  }

  return (await response.json()) as AssistantProcessResponse
}
