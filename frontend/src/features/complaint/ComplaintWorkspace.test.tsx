import { configureStore } from '@reduxjs/toolkit'
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { Provider } from 'react-redux'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { isComplaintEmpty } from './complaintDisplay'
import complaintReducer, {
  applyFieldPatch,
  setComplaintStatus,
} from './complaintSlice'
import {
  createEmptyComplaintFieldValue,
  createInitialComplaintDraftState,
  type ComplaintDraftState,
} from './complaintTypes'
import { ComplaintWorkspace } from './components/ComplaintWorkspace'
import styles from './components/ComplaintField.module.css'

function createStore(preloaded?: ComplaintDraftState) {
  return configureStore({
    reducer: { complaint: complaintReducer },
    preloadedState: preloaded ? { complaint: preloaded } : undefined,
  })
}

function renderWorkspace(preloaded?: ComplaintDraftState) {
  const store = createStore(preloaded)
  const view = render(
    <Provider store={store}>
      <ComplaintWorkspace />
    </Provider>,
  )
  return { store, ...view }
}

function showComplaintPane() {
  fireEvent.click(screen.getByRole('tab', { name: 'Complaint' }))
}

describe('ComplaintWorkspace UI', () => {
  beforeEach(() => {
    HTMLDialogElement.prototype.showModal = function showModal() {
      this.setAttribute('open', '')
    }
    HTMLDialogElement.prototype.close = function close() {
      this.removeAttribute('open')
    }
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders the complaint and assistant workspace', () => {
    renderWorkspace()

    expect(
      screen.getByRole('heading', { name: 'Log Customer Complaint' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'VeyraQ Assistant' }),
    ).toBeInTheDocument()
  })

  it('renders canonical field labels', () => {
    renderWorkspace()
    showComplaintPane()

    expect(screen.getByLabelText('Customer Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Product Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Batch / Lot Number')).toBeInTheDocument()
    expect(screen.getByLabelText('Affected Quantity')).toBeInTheDocument()
    expect(screen.getByLabelText('Complaint Description')).toBeInTheDocument()
    expect(screen.getByLabelText('Initial Risk Assessment')).toBeInTheDocument()
  })

  it('updates Redux on user edit with user provenance and leaves unrelated fields alone', () => {
    const { store } = renderWorkspace()
    showComplaintPane()
    const unrelatedBefore = store.getState().complaint.fields.customer_name

    fireEvent.change(screen.getByLabelText('Product Name'), {
      target: { value: 'Amoxicillin Capsules' },
    })

    const state = store.getState().complaint
    expect(state.fields.product_name).toEqual({
      value: 'Amoxicillin Capsules',
      provenance: 'user',
      confidence: null,
      evidence: null,
    })
    expect(state.fields.customer_name).toEqual(unrelatedBefore)
  })

  it('stores null when a field is cleared', () => {
    const { store } = renderWorkspace()
    showComplaintPane()

    const input = screen.getByLabelText('Customer Name')
    fireEvent.change(input, { target: { value: 'Apollo Pharmacy' } })
    fireEvent.change(input, { target: { value: '' } })

    expect(store.getState().complaint.fields.customer_name.value).toBeNull()
    expect(store.getState().complaint.fields.customer_name.provenance).toBe(
      'user',
    )
  })

  it('preserves partial date text exactly', () => {
    const { store } = renderWorkspace()
    showComplaintPane()

    fireEvent.change(screen.getByLabelText('Manufacturing Date'), {
      target: { value: 'March 2026' },
    })

    expect(store.getState().complaint.fields.manufacturing_date.value).toBe(
      'March 2026',
    )
  })

  it('reset confirmation cancel preserves draft and confirm clears it', () => {
    const { store } = renderWorkspace()
    showComplaintPane()
    fireEvent.change(screen.getByLabelText('Customer Name'), {
      target: { value: 'Apollo Pharmacy' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Reset Complaint' }))
    const dialog = screen.getByRole('dialog')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
    expect(store.getState().complaint.fields.customer_name.value).toBe(
      'Apollo Pharmacy',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Reset Complaint' }))
    fireEvent.click(
      within(screen.getByRole('dialog')).getByRole('button', {
        name: 'Reset Complaint',
      }),
    )
    expect(store.getState().complaint.fields.customer_name.value).toBeNull()
    expect(store.getState().complaint.status).toBe('pending_triage')
  })

  it('disables commit while pending triage and enables when ready_to_commit', () => {
    const { store } = renderWorkspace()
    showComplaintPane()
    expect(
      screen.getByRole('button', { name: 'Commit Complaint' }),
    ).toBeDisabled()

    act(() => {
      store.dispatch(setComplaintStatus('ready_to_commit'))
    })
    expect(
      screen.getByRole('button', { name: 'Commit Complaint' }),
    ).toBeEnabled()
  })

  it('shows provenance labels for source, user, and inferred values', () => {
    const preloaded = createInitialComplaintDraftState()
    preloaded.fields.product_name = {
      value: 'Amoxicillin Capsules',
      provenance: 'source',
      confidence: null,
      evidence: null,
    }
    preloaded.fields.customer_name = {
      value: 'Apollo Pharmacy',
      provenance: 'user',
      confidence: null,
      evidence: null,
    }
    preloaded.fields.initial_severity = {
      value: 'Medium',
      provenance: 'inferred',
      confidence: null,
      evidence: null,
    }

    renderWorkspace(preloaded)
    showComplaintPane()

    expect(screen.getByText('Extracted')).toBeInTheDocument()
    expect(screen.getByText('User edited')).toBeInTheDocument()
    expect(screen.getByText('AI suggestion · Verify')).toBeInTheDocument()
  })

  it('highlights recently updated fields and clears highlight via UI timer', () => {
    vi.useFakeTimers()
    const { store } = renderWorkspace()
    showComplaintPane()

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

    const fieldRoot = document.querySelector(
      '[data-field-key="batch_lot_number"]',
    )
    expect(fieldRoot?.className).toContain(styles.recentlyUpdated)

    act(() => {
      vi.advanceTimersByTime(1250)
    })
    expect(store.getState().complaint.recentlyUpdatedFields).toEqual([])
  })

  it('shows Not provided metadata for empty fields without putting it in the input', () => {
    renderWorkspace()
    showComplaintPane()
    const input = screen.getByLabelText('Product Name') as HTMLInputElement
    expect(input.value).toBe('')
    expect(screen.getAllByText('Not provided').length).toBeGreaterThan(0)
  })
})

describe('complaintDisplay helpers used by UI', () => {
  it('treats all-null fields as empty', () => {
    const fields = createInitialComplaintDraftState().fields
    expect(isComplaintEmpty(fields)).toBe(true)
    fields.product_name = {
      ...createEmptyComplaintFieldValue(),
      value: 'x',
      provenance: 'user',
    }
    expect(isComplaintEmpty(fields)).toBe(false)
  })
})
