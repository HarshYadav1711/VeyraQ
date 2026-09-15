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
import complaintReducer, { setComplaintStatus } from '../complaint/complaintSlice'
import {
  createInitialComplaintDraftState,
  type ComplaintDraftState,
  type ComplaintFieldValue,
} from '../complaint/complaintTypes'
import { ComplaintWorkspace } from '../complaint/components/ComplaintWorkspace'
import fieldStyles from '../complaint/components/ComplaintField.module.css'

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
  state.fields.product_strength_grade = field('500 mg')
  state.fields.batch_lot_number = field('AMX240602')
  state.fields.affected_quantity = field('12 capsules')
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

const SUCCESS_BODY = {
  intent: 'new_complaint',
  patch: {
    changes: {
      customer_name: {
        value: 'NovaCare Pharmacy',
        provenance: 'source',
        confidence: null,
        evidence: 'NovaCare Pharmacy',
      },
      product_name: {
        value: 'Cefixime Capsules',
        provenance: 'source',
        confidence: null,
        evidence: 'Cefixime Capsules',
      },
      batch_lot_number: {
        value: 'CFX260481',
        provenance: 'source',
        confidence: null,
        evidence: 'CFX260481',
      },
      complaint_description: {
        value: 'NovaCare Pharmacy reported brown discoloration.',
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
        value: 'Discoloration should be investigated by QA.',
        provenance: 'inferred',
        confidence: null,
        evidence: null,
      },
    },
  },
  status: 'needs_information',
  missing_required_fields: ['complaint_source'],
  assistant_message:
    'I extracted the available complaint details. I still need: Complaint Source before this record can be ready for review.',
  warnings: [],
}

describe('Assistant text workflow', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('enables the Assistant composer', () => {
    renderWorkspace()
    const composer = screen.getByLabelText('Complaint input')
    expect(composer).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Choose file' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Analyze Document' })).toBeDisabled()
  })

  it('does not submit whitespace-only messages', () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    renderWorkspace()

    fireEvent.change(screen.getByLabelText('Complaint input'), {
      target: { value: '   \n  ' },
    })
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('shows the user message and processing state on submit', async () => {
    let resolveFetch: (value: unknown) => void = () => undefined
    const fetchMock = vi.fn(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve
        }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const store = renderWorkspace()

    fireEvent.change(screen.getByLabelText('Complaint input'), {
      target: { value: 'NovaCare Pharmacy reported brown discoloration.' },
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    })

    expect(
      screen.getByText('NovaCare Pharmacy reported brown discoloration.'),
    ).toBeInTheDocument()
    await waitFor(() => {
      expect(store.getState().assistant.requestStatus).toBe('processing')
      expect(store.getState().complaint.status).toBe('processing')
    })
    expect(screen.getByText('Processing complaint…')).toBeInTheDocument()

    await act(async () => {
      resolveFetch({
        ok: true,
        json: async () => SUCCESS_BODY,
      })
    })
  })

  it('applies a successful extraction patch and provenance labels', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => SUCCESS_BODY,
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
        'Cefixime Capsules',
      )
    })

    fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
    expect(screen.getAllByText('Extracted').length).toBeGreaterThan(0)
    expect(screen.getAllByText('AI suggestion · Verify').length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('tab', { name: 'Assistant' }))
    expect(
      screen.getByText(/I extracted the available complaint details/),
    ).toBeInTheDocument()
    expect(store.getState().complaint.status).toBe('needs_information')
    expect(
      screen.getByRole('button', { name: 'Commit Complaint' }),
    ).toBeDisabled()
  })

  it('enables Commit when the response is ready_to_commit', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          ...SUCCESS_BODY,
          status: 'ready_to_commit',
          missing_required_fields: [],
          assistant_message:
            'I extracted the complaint and prepared an initial risk assessment. The record is ready for QA review.',
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
      expect(store.getState().complaint.status).toBe('ready_to_commit')
    })
    expect(
      screen.getByRole('button', { name: 'Commit Complaint' }),
    ).toBeEnabled()
  })

  it('applies only returned correction fields and highlights them', async () => {
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
              affected_quantity: {
                value: '48 capsules',
                provenance: 'user',
                confidence: null,
                evidence: null,
              },
            },
          },
          status: 'needs_information',
          missing_required_fields: ['complaint_category', 'initial_risk_assessment'],
          assistant_message: 'Updated Batch / Lot Number and Affected Quantity.',
          warnings: [],
        }),
      }),
    )
    const store = renderWorkspace(populatedState())
    const productBefore = store.getState().complaint.fields.product_name
    fireEvent.click(screen.getByRole('tab', { name: 'Assistant' }))
    fireEvent.change(screen.getByLabelText('Complaint input'), {
      target: {
        value: 'Sorry, the batch is BMX240602 and 48 capsules were affected.',
      },
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    })

    await waitFor(() => {
      expect(store.getState().complaint.fields.batch_lot_number.value).toBe(
        'BMX240602',
      )
    })
    expect(store.getState().complaint.fields.affected_quantity.value).toBe(
      '48 capsules',
    )
    expect(store.getState().complaint.fields.product_name).toEqual(productBefore)
    expect(store.getState().complaint.recentlyUpdatedFields).toEqual([
      'batch_lot_number',
      'affected_quantity',
    ])

    fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
    const batchRoot = document.querySelector('[data-field-key="batch_lot_number"]')
    expect(batchRoot?.className).toContain(fieldStyles.recentlyUpdated)
  })

  it('preserves the draft and allows retry when the API fails', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: async () => ({
          detail:
            'AI processing is temporarily unavailable. Your complaint draft has not been changed.',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => SUCCESS_BODY,
      })
    vi.stubGlobal('fetch', fetchMock)
    const store = renderWorkspace(populatedState())
    fireEvent.click(screen.getByRole('tab', { name: 'Assistant' }))
    fireEvent.change(screen.getByLabelText('Complaint input'), {
      target: { value: 'Sorry, the batch is BMX240602.' },
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    })

    await waitFor(() => {
      expect(store.getState().assistant.requestStatus).toBe('failed')
    })
    expect(store.getState().complaint.status).toBe('needs_information')
    expect(store.getState().complaint.fields.product_name.value).toBe(
      'Amoxicillin Capsules',
    )
    expect(store.getState().complaint.fields.batch_lot_number.value).toBe(
      'AMX240602',
    )
    expect(screen.getByRole('alert')).toHaveTextContent(
      'AI processing is temporarily unavailable',
    )
    expect(screen.getByRole('button', { name: 'Retry' })).toBeEnabled()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    })
    await waitFor(() => {
      expect(store.getState().complaint.fields.product_name.value).toBe(
        'Cefixime Capsules',
      )
    })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})

describe('commit remains available after AI wiring', () => {
  beforeEach(() => {
    HTMLDialogElement.prototype.showModal = function showModal() {
      this.setAttribute('open', '')
    }
    HTMLDialogElement.prototype.close = function close() {
      this.removeAttribute('open')
    }
  })

  it('can mark ready_to_commit and keep commit enabled', () => {
    const store = renderWorkspace()
    fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
    act(() => {
      store.dispatch(setComplaintStatus('ready_to_commit'))
    })
    expect(
      screen.getByRole('button', { name: 'Commit Complaint' }),
    ).toBeEnabled()
  })
})
