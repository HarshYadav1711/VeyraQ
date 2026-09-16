import { configureStore } from '@reduxjs/toolkit'
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { Provider } from 'react-redux'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import assistantReducer from './assistantSlice'
import complaintReducer, {
  resetComplaintDraft,
  setComplaintStatus,
} from '../complaint/complaintSlice'
import {
  createInitialComplaintDraftState,
  type ComplaintDraftState,
  type ComplaintFieldValue,
} from '../complaint/complaintTypes'
import { ComplaintWorkspace } from '../complaint/components/ComplaintWorkspace'

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

const RELATED_MATCH = {
  complaint_id: '11111111-1111-4111-8111-111111111101',
  complaint_number: 'CMP-DEMO-0001',
  score: 0.91,
  match_strength: 'strong',
  reasons: [
    'Same product',
    'Same batch / lot',
    'Same complaint category',
    'Similar complaint description',
  ],
  product_name: 'Cefixime Capsules 200 mg',
  batch_lot_number: 'CFX260481',
  customer_name: 'Northbridge Pharmacy',
  complaint_category: 'Product Defect – Discoloration',
  complaint_description: 'Brown discoloration observed on multiple capsules.',
  committed_at: '2026-03-10T00:00:00Z',
}

const SUCCESS_WITH_RELATED = {
  intent: 'new_complaint',
  patch: {
    changes: {
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
      initial_severity: {
        value: 'Major',
        provenance: 'inferred',
        confidence: null,
        evidence: null,
      },
      initial_risk_assessment: {
        value: 'Investigate discoloration.',
        provenance: 'inferred',
        confidence: null,
        evidence: null,
      },
    },
  },
  status: 'needs_information',
  missing_required_fields: ['complaint_source', 'customer_name'],
  assistant_message:
    'I extracted the available complaint details. I still need: Complaint Source and Customer Name before this record can be ready for review. I also found 1 potentially related historical complaint.',
  warnings: [],
  related_complaints: [RELATED_MATCH],
  related_lookup_evaluated: true,
}

describe('Related complaints UI', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('renders related complaint cards from a successful AI response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => SUCCESS_WITH_RELATED,
      }),
    )
    const store = renderWorkspace()
    fireEvent.change(screen.getByLabelText('Complaint input'), {
      target: {
        value:
          'NovaCare Pharmacy reported brown discoloration on Cefixime Capsules 200 mg from batch CFX260481.',
      },
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    })

    await waitFor(() => {
      expect(store.getState().assistant.relatedComplaints).toHaveLength(1)
    })
    fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
    expect(screen.getByText('Potential Related Complaints')).toBeInTheDocument()
    expect(screen.getByText('CMP-DEMO-0001')).toBeInTheDocument()
    expect(screen.getByText('Strong match')).toBeInTheDocument()
    expect(screen.getByText('Cefixime Capsules 200 mg')).toBeInTheDocument()
    expect(screen.getByText(/Batch CFX260481/)).toBeInTheDocument()
    expect(screen.getByText('Same product')).toBeInTheDocument()
    expect(store.getState().complaint.fields).not.toHaveProperty(
      'related_complaints',
    )
  })

  it('replaces prior related results on a later Assistant response', async () => {
    const secondMatch = {
      ...RELATED_MATCH,
      complaint_id: '22222222-2222-4222-8222-222222222202',
      complaint_number: 'CMP-DEMO-0002',
      score: 0.88,
    }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => SUCCESS_WITH_RELATED,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          intent: 'correction',
          patch: {
            changes: {
              batch_lot_number: {
                value: 'CFX260481',
                provenance: 'user',
                confidence: null,
                evidence: null,
              },
            },
          },
          status: 'needs_information',
          missing_required_fields: ['complaint_source'],
          assistant_message: 'Updated Batch / Lot Number.',
          warnings: [],
          related_complaints: [secondMatch],
          related_lookup_evaluated: true,
        }),
      })
    vi.stubGlobal('fetch', fetchMock)
    const store = renderWorkspace()
    fireEvent.change(screen.getByLabelText('Complaint input'), {
      target: { value: 'Cefixime Capsules 200 mg batch CFX260481 discoloration.' },
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    })
    await waitFor(() => {
      expect(store.getState().assistant.relatedComplaints[0]?.complaint_number).toBe(
        'CMP-DEMO-0001',
      )
    })

    fireEvent.change(screen.getByLabelText('Complaint input'), {
      target: { value: 'The batch is CFX260481.' },
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    })
    await waitFor(() => {
      expect(store.getState().assistant.relatedComplaints[0]?.complaint_number).toBe(
        'CMP-DEMO-0002',
      )
    })
    expect(store.getState().assistant.relatedComplaints).toHaveLength(1)
  })

  it('clears related results on Reset / New Complaint', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => SUCCESS_WITH_RELATED,
      }),
    )
    const store = renderWorkspace()
    fireEvent.change(screen.getByLabelText('Complaint input'), {
      target: { value: 'Cefixime Capsules 200 mg batch CFX260481 discoloration.' },
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    })
    await waitFor(() => {
      expect(store.getState().assistant.relatedComplaints).toHaveLength(1)
    })

    act(() => {
      store.dispatch(resetComplaintDraft())
    })
    expect(store.getState().assistant.relatedComplaints).toEqual([])
    expect(store.getState().assistant.relatedLookupEvaluated).toBe(false)
  })

  it('does not create a noisy empty UI when related lookup was not evaluated', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          ...SUCCESS_WITH_RELATED,
          related_complaints: [],
          related_lookup_evaluated: false,
          assistant_message: 'I extracted the available complaint details.',
        }),
      }),
    )
    renderWorkspace()
    fireEvent.change(screen.getByLabelText('Complaint input'), {
      target: { value: 'Short note without enough product detail.' },
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    })
    await waitFor(() => {
      expect(screen.getByText(/I extracted the available complaint details/)).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
    expect(
      screen.queryByText('Potential Related Complaints'),
    ).not.toBeInTheDocument()
  })

  it('shows a restrained no-match message when evaluated with zero results', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          ...SUCCESS_WITH_RELATED,
          related_complaints: [],
          related_lookup_evaluated: true,
          assistant_message: 'I extracted the available complaint details.',
        }),
      }),
    )
    renderWorkspace()
    fireEvent.change(screen.getByLabelText('Complaint input'), {
      target: { value: 'Unique product ZX-99 with unusual defect narrative.' },
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    })
    await waitFor(() => {
      expect(screen.getByText(/I extracted the available complaint details/)).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
    expect(
      screen.getByText('No closely related committed complaints found.'),
    ).toBeInTheDocument()
  })
})

describe('existing workflows remain functional with related UI', () => {
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

  it('keeps text correction and commit paths working', async () => {
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
          status: 'ready_to_commit',
          missing_required_fields: [],
          assistant_message: 'Updated Batch / Lot Number.',
          warnings: [],
          related_complaints: [],
          related_lookup_evaluated: true,
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
    act(() => {
      store.dispatch(setComplaintStatus('ready_to_commit'))
    })
    fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
    expect(
      screen.getByRole('button', { name: 'Commit Complaint' }),
    ).toBeEnabled()
  })
})
