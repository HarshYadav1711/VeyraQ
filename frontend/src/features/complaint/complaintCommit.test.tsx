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
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import assistantReducer from '../assistant/assistantSlice'
import complaintReducer, {
  commitComplaint,
  setComplaintStatus,
} from './complaintSlice'
import {
  createInitialComplaintDraftState,
  serializeCommitRequest,
  type ComplaintDraftState,
  type ComplaintFields,
} from './complaintTypes'
import { ComplaintWorkspace } from './components/ComplaintWorkspace'

function filledFields(): ComplaintFields {
  const fields = createInitialComplaintDraftState().fields
  const values: Partial<Record<keyof ComplaintFields, string>> = {
    complaint_source: 'Email',
    customer_name: 'Northbridge Pharmacy',
    product_name: 'Amoxicillin Capsules',
    batch_lot_number: 'BMX240602',
    complaint_category: 'Packaging Defect',
    complaint_description: 'Blister seal incomplete.',
    initial_risk_assessment: 'Limited packaging risk.',
    manufacturing_date: 'March 2026',
  }
  for (const [key, value] of Object.entries(values)) {
    fields[key as keyof ComplaintFields] = {
      value,
      provenance: 'user',
      confidence: null,
      evidence: null,
    }
  }
  return fields
}

function readyState(): ComplaintDraftState {
  return {
    ...createInitialComplaintDraftState(),
    fields: filledFields(),
    status: 'ready_to_commit',
  }
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
  fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
  return store
}

function mockCommitSuccess() {
  return vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
      complaint_number: 'CMP-2026-A1B2C3',
      status: 'committed',
      fields: filledFields(),
      created_at: '2026-09-15T12:00:00Z',
      committed_at: '2026-09-15T12:00:00Z',
    }),
  })
}

describe('complaint commit flow', () => {
  beforeEach(() => {
    HTMLDialogElement.prototype.showModal = function showModal() {
      this.setAttribute('open', '')
    }
    HTMLDialogElement.prototype.close = function close() {
      this.removeAttribute('open')
    }
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('enables commit when ready_to_commit', () => {
    renderWorkspace(readyState())
    expect(
      screen.getByRole('button', { name: 'Commit Complaint' }),
    ).toBeEnabled()
  })

  it('posts commit payload and locks fields on success', async () => {
    const fetchMock = mockCommitSuccess()
    vi.stubGlobal('fetch', fetchMock)

    const store = renderWorkspace(readyState())
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Commit Complaint' }))
    })

    await waitFor(() => {
      expect(store.getState().complaint.status).toBe('committed')
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://localhost:8000/api/v1/complaints/commit')
    expect(init.method).toBe('POST')
    expect(JSON.parse(String(init.body))).toEqual(
      serializeCommitRequest(filledFields()),
    )
    expect(screen.getByText('CMP-2026-A1B2C3')).toBeInTheDocument()
    expect(screen.getByLabelText('Product Name')).toBeDisabled()
    expect(
      screen.getByRole('button', { name: 'Commit Complaint' }),
    ).toBeDisabled()
  })

  it('keeps draft and shows error on failed commit', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: { detail: 'Unable to persist complaint' } }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const store = renderWorkspace(readyState())
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Commit Complaint' }))
    })

    await waitFor(() => {
      expect(store.getState().complaint.commitStatus).toBe('failed')
    })

    expect(store.getState().complaint.status).toBe('ready_to_commit')
    expect(store.getState().complaint.fields.product_name.value).toBe(
      'Amoxicillin Capsules',
    )
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Unable to persist complaint',
    )
    expect(
      screen.getByRole('button', { name: 'Commit Complaint' }),
    ).toBeEnabled()
  })

  it('prevents duplicate submission while submitting', async () => {
    let resolveFetch: (value: unknown) => void = () => undefined
    const fetchMock = vi.fn().mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve
        }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const store = renderWorkspace(readyState())
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Commit Complaint' }))
    })

    await waitFor(() => {
      expect(store.getState().complaint.commitStatus).toBe('submitting')
    })
    expect(screen.getByRole('button', { name: 'Committing…' })).toBeDisabled()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Committing…' }))
    })
    expect(fetchMock).toHaveBeenCalledTimes(1)

    await act(async () => {
      resolveFetch({
        ok: true,
        json: async () => ({
          id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
          complaint_number: 'CMP-2026-A1B2C3',
          status: 'committed',
          fields: filledFields(),
          created_at: '2026-09-15T12:00:00Z',
          committed_at: '2026-09-15T12:00:00Z',
        }),
      })
    })

    await waitFor(() => {
      expect(store.getState().complaint.status).toBe('committed')
    })
  })

  it('new complaint after commit clears persistence metadata', () => {
    const store = createStore({
      ...readyState(),
      status: 'committed',
      commitStatus: 'succeeded',
      committedRecordId: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
      complaintNumber: 'CMP-2026-A1B2C3',
    })
    render(
      <Provider store={store}>
        <ComplaintWorkspace />
      </Provider>,
    )
    fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))

    fireEvent.click(screen.getByRole('button', { name: 'New Complaint' }))
    const dialog = screen.getByRole('dialog')
    fireEvent.click(
      within(dialog).getByRole('button', { name: 'New Complaint' }),
    )

    const state = store.getState().complaint
    expect(state.status).toBe('pending_triage')
    expect(state.committedRecordId).toBeNull()
    expect(state.complaintNumber).toBeNull()
    expect(state.commitStatus).toBe('idle')
    expect(state.fields.product_name.value).toBeNull()
  })
})

describe('serializeCommitRequest', () => {
  it('keeps null values and omits presentation labels', () => {
    const fields = createInitialComplaintDraftState().fields
    fields.product_name = {
      value: 'Amoxicillin Capsules',
      provenance: 'source',
      confidence: 0.9,
      evidence: 'Amoxicillin Capsules',
    }
    const body = serializeCommitRequest(fields)
    expect(body.fields.product_name.value).toBe('Amoxicillin Capsules')
    expect(body.fields.customer_name.value).toBeNull()
    expect(JSON.stringify(body)).not.toContain('Not provided')
    expect(JSON.stringify(body)).not.toContain('Extracted')
  })
})

describe('commitComplaint thunk guards', () => {
  it('rejects when status is not ready_to_commit', async () => {
    const store = createStore()
    const result = await store.dispatch(commitComplaint())
    expect(result.meta.requestStatus).toBe('rejected')
    expect(store.getState().complaint.status).toBe('pending_triage')
  })

  it('can mark ready for tests via setComplaintStatus', () => {
    const store = createStore()
    store.dispatch(setComplaintStatus('ready_to_commit'))
    expect(store.getState().complaint.status).toBe('ready_to_commit')
  })
})
