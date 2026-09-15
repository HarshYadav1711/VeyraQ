import type {
  ComplaintCommitRequest,
  CommittedComplaintResponse,
} from './complaintTypes'

function apiBaseUrl(): string {
  const base = import.meta.env.VITE_API_BASE_URL
  if (typeof base !== 'string' || base.trim() === '') {
    throw new Error('VITE_API_BASE_URL is not configured')
  }
  return base.replace(/\/$/, '')
}

export class ComplaintApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ComplaintApiError'
    this.status = status
  }
}

export async function postCommitComplaint(
  body: ComplaintCommitRequest,
): Promise<CommittedComplaintResponse> {
  const response = await fetch(`${apiBaseUrl()}/complaints/commit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    let message = 'Unable to commit complaint. Please try again.'
    try {
      const payload = (await response.json()) as {
        detail?: { detail?: string; missing_fields?: string[] } | string
      }
      if (typeof payload.detail === 'string') {
        message = payload.detail
      } else if (payload.detail && typeof payload.detail === 'object') {
        if (payload.detail.missing_fields?.length) {
          message = `Missing required fields: ${payload.detail.missing_fields.join(', ')}`
        } else if (payload.detail.detail) {
          message = payload.detail.detail
        }
      }
    } catch {
      // Keep the safe default message.
    }
    throw new ComplaintApiError(message, response.status)
  }

  return (await response.json()) as CommittedComplaintResponse
}
