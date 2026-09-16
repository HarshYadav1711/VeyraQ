import { configureStore } from '@reduxjs/toolkit'
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { Provider } from 'react-redux'
import { afterEach, describe, expect, it, vi } from 'vitest'

import assistantReducer from './assistantSlice'
import complaintReducer, {
  applyFieldPatch,
  resetComplaintDraft,
  setUserField,
} from '../complaint/complaintSlice'
import {
  createInitialComplaintDraftState,
  type ComplaintDraftState,
  type ComplaintFieldValue,
} from '../complaint/complaintTypes'
import { ComplaintWorkspace } from '../complaint/components/ComplaintWorkspace'

function field(
  value: string | null,
  provenance: ComplaintFieldValue['provenance'] = 'source',
): ComplaintFieldValue {
  if (value === null) {
    return {
      value: null,
      provenance: 'missing',
      confidence: null,
      evidence: null,
    }
  }
  return {
    value,
    provenance,
    confidence: null,
    evidence: provenance === 'source' ? value : null,
  }
}

function readyDraft(): ComplaintDraftState {
  const state = createInitialComplaintDraftState()
  state.fields.product_name = field('Cefixime Capsules 200 mg')
  state.fields.complaint_description = field(
    'Brown discoloration was observed on several capsules.',
  )
  state.fields.batch_lot_number = field('CFX260481')
  state.fields.initial_severity = field('Major', 'inferred')
  state.fields.priority = field('High', 'inferred')
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

const INVESTIGATION_BODY = {
  complaint_summary:
    'A customer reported brown discoloration on Cefixime Capsules 200 mg. QA should review the complaint and batch context.',
  root_cause_hypotheses: [
    {
      category: 'material',
      hypothesis:
        'Packaging material may have contributed to moisture exposure.',
      rationale:
        'The complaint concerns capsule discoloration and packaging should be investigated.',
      supporting_fields: ['complaint_description', 'product_name'],
      evidence_needed: [
        'Packaging material records',
        'Container-closure inspection',
        'Retain sample review',
      ],
    },
  ],
  capa_suggestions: [
    {
      type: 'immediate_correction',
      action: 'Quarantine remaining implicated stock pending QA review.',
      rationale: 'Containment while the discoloration complaint is investigated.',
    },
    {
      type: 'corrective_action',
      action:
        'If investigation confirms a packaging contribution, review packaging controls.',
      rationale: 'Addresses a potential packaging-related cause if supported.',
    },
  ],
  related_history_used: false,
}

describe('Investigation Assistance', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('disables generation without minimum context', () => {
    renderWorkspace()
    fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
    expect(
      screen.getByRole('button', { name: 'Generate Investigation Assistance' }),
    ).toBeDisabled()
    expect(
      screen.getByText(/Product Name and Complaint Description are required/),
    ).toBeInTheDocument()
  })

  it('enables generation with product and description', () => {
    renderWorkspace(readyDraft())
    fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
    expect(
      screen.getByRole('button', { name: 'Generate Investigation Assistance' }),
    ).toBeEnabled()
  })

  it('calls the investigation endpoint and renders results', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => INVESTIGATION_BODY,
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = renderWorkspace(readyDraft())
    const severityBefore = store.getState().complaint.fields.initial_severity
    const priorityBefore = store.getState().complaint.fields.priority
    const statusBefore = store.getState().complaint.status

    fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
    await act(async () => {
      fireEvent.click(
        screen.getByRole('button', { name: 'Generate Investigation Assistance' }),
      )
    })

    await waitFor(() => {
      expect(store.getState().assistant.investigationStatus).toBe('ready')
    })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/assistant/investigation')
    expect(init.method).toBe('POST')
    expect(screen.getByText(/AI Complaint Summary/)).toBeInTheDocument()
    expect(
      screen.getByText(/brown discoloration on Cefixime Capsules 200 mg/i),
    ).toBeInTheDocument()
    expect(screen.getByText('Root Cause Hypotheses')).toBeInTheDocument()
    expect(screen.getByText('Material')).toBeInTheDocument()
    expect(
      screen.getByText(/Packaging material may have contributed/),
    ).toBeInTheDocument()
    expect(screen.getByText('Packaging material records')).toBeInTheDocument()
    expect(screen.getByText('CAPA Suggestions')).toBeInTheDocument()
    expect(screen.getByText('Immediate Correction')).toBeInTheDocument()
    expect(store.getState().complaint.fields.initial_severity).toEqual(
      severityBefore,
    )
    expect(store.getState().complaint.fields.priority).toEqual(priorityBefore)
    expect(store.getState().complaint.status).toBe(statusBefore)
    expect(store.getState().complaint.fields).not.toHaveProperty(
      'complaint_summary',
    )
  })

  it('prevents duplicate investigation requests while loading', async () => {
    let resolveFetch: (value: unknown) => void = () => undefined
    const fetchMock = vi.fn(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve
        }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const store = renderWorkspace(readyDraft())
    fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
    await act(async () => {
      fireEvent.click(
        screen.getByRole('button', { name: 'Generate Investigation Assistance' }),
      )
    })
    await waitFor(() => {
      expect(store.getState().assistant.investigationStatus).toBe('processing')
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Preparing…' }))
    })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    await act(async () => {
      resolveFetch({
        ok: true,
        json: async () => INVESTIGATION_BODY,
      })
    })
  })

  it('clears stale investigation after manual field edit', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => INVESTIGATION_BODY,
      }),
    )
    const store = renderWorkspace(readyDraft())
    fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
    await act(async () => {
      fireEvent.click(
        screen.getByRole('button', { name: 'Generate Investigation Assistance' }),
      )
    })
    await waitFor(() => {
      expect(store.getState().assistant.investigationAssistance).not.toBeNull()
    })
    act(() => {
      store.dispatch(
        setUserField({ field: 'batch_lot_number', value: 'CFX260418' }),
      )
    })
    expect(store.getState().assistant.investigationAssistance).toBeNull()
  })

  it('clears stale investigation after AI field patch', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => INVESTIGATION_BODY,
      }),
    )
    const store = renderWorkspace(readyDraft())
    fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
    await act(async () => {
      fireEvent.click(
        screen.getByRole('button', { name: 'Generate Investigation Assistance' }),
      )
    })
    await waitFor(() => {
      expect(store.getState().assistant.investigationAssistance).not.toBeNull()
    })
    act(() => {
      store.dispatch(
        applyFieldPatch({
          changes: {
            batch_lot_number: {
              value: 'BMX240602',
              provenance: 'user',
              confidence: null,
              evidence: null,
            },
          },
        }),
      )
    })
    expect(store.getState().assistant.investigationAssistance).toBeNull()
  })

  it('clears investigation on Reset / New Complaint', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => INVESTIGATION_BODY,
      }),
    )
    const store = renderWorkspace(readyDraft())
    fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
    await act(async () => {
      fireEvent.click(
        screen.getByRole('button', { name: 'Generate Investigation Assistance' }),
      )
    })
    await waitFor(() => {
      expect(store.getState().assistant.investigationAssistance).not.toBeNull()
    })
    act(() => {
      store.dispatch(resetComplaintDraft())
    })
    expect(store.getState().assistant.investigationAssistance).toBeNull()
    expect(store.getState().assistant.investigationStatus).toBe('idle')
  })

  it('preserves complaint fields when investigation fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({
          detail:
            'Investigation assistance is temporarily unavailable. Your complaint record has not been changed.',
        }),
      }),
    )
    const store = renderWorkspace(readyDraft())
    const before = store.getState().complaint.fields.product_name
    fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
    await act(async () => {
      fireEvent.click(
        screen.getByRole('button', { name: 'Generate Investigation Assistance' }),
      )
    })
    await waitFor(() => {
      expect(store.getState().assistant.investigationStatus).toBe('failed')
    })
    expect(store.getState().complaint.fields.product_name).toEqual(before)
    expect(screen.getByRole('alert')).toHaveTextContent(
      /Investigation assistance is temporarily unavailable/,
    )
  })

  it('does not run investigation during ordinary assistant process', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        intent: 'new_complaint',
        patch: { changes: {} },
        status: 'needs_information',
        missing_required_fields: ['batch_lot_number'],
        assistant_message: 'I extracted the available complaint details.',
        warnings: [],
        related_complaints: [],
        related_lookup_evaluated: true,
      }),
    })
    vi.stubGlobal('fetch', fetchMock)
    renderWorkspace()
    fireEvent.change(screen.getByLabelText('Complaint input'), {
      target: { value: 'A short complaint about Cefixime Capsules 200 mg.' },
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    })
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled()
    })
    expect(
      fetchMock.mock.calls.every(
        (call) => !String(call[0]).includes('/assistant/investigation'),
      ),
    ).toBe(true)
  })
})
