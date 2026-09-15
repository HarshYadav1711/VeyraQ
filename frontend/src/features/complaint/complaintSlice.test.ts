import { configureStore } from '@reduxjs/toolkit'
import { describe, expect, it } from 'vitest'

import complaintReducer, {
  applyFieldPatch,
  resetComplaintDraft,
  setComplaintStatus,
  setUserField,
} from './complaintSlice'
import {
  COMPLAINT_FIELD_KEYS,
  createEmptyComplaintFieldValue,
  createInitialComplaintDraftState,
  type ComplaintDraftState,
  type ComplaintFieldKey,
  type ComplaintFieldValue,
} from './complaintTypes'

function createTestStore(preloadedState?: ComplaintDraftState) {
  return configureStore({
    reducer: { complaint: complaintReducer },
    preloadedState: preloadedState
      ? { complaint: preloadedState }
      : undefined,
  })
}

function field(
  value: string,
  provenance: ComplaintFieldValue['provenance'] = 'source',
): ComplaintFieldValue {
  return {
    value,
    provenance,
    confidence: null,
    evidence: null,
  }
}

describe('complaintTypes', () => {
  it('initial fields are null with missing provenance', () => {
    const state = createInitialComplaintDraftState()

    expect(state.status).toBe('pending_triage')
    expect(state.recentlyUpdatedFields).toEqual([])
    for (const key of COMPLAINT_FIELD_KEYS) {
      expect(state.fields[key]).toEqual(createEmptyComplaintFieldValue())
    }
  })
})

describe('complaintSlice', () => {
  it('setUserField updates only the target field with user provenance', () => {
    const store = createTestStore()
    const beforeCustomer = store.getState().complaint.fields.customer_name

    store.dispatch(setUserField({ field: 'product_name', value: 'Amoxicillin Capsules' }))

    const state = store.getState().complaint
    expect(state.fields.product_name).toEqual({
      value: 'Amoxicillin Capsules',
      provenance: 'user',
      confidence: null,
      evidence: null,
    })
    expect(state.fields.customer_name).toBe(beforeCustomer)
    expect(state.recentlyUpdatedFields).toEqual(['product_name'])
  })

  it('applyFieldPatch changes only listed fields and preserves unrelated objects', () => {
    const starting: ComplaintDraftState = {
      ...createInitialComplaintDraftState(),
      fields: {
        ...createInitialComplaintDraftState().fields,
        product_name: field('Amoxicillin Capsules'),
        product_strength_grade: field('500 mg'),
        batch_lot_number: field('AMX240602'),
        affected_quantity: field('12 capsules'),
        customer_name: field('Apollo Pharmacy'),
      },
      status: 'pending_triage',
    }

    const productNameRef = starting.fields.product_name
    const strengthRef = starting.fields.product_strength_grade
    const customerRef = starting.fields.customer_name

    const store = createTestStore(starting)
    store.dispatch(
      applyFieldPatch({
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
      }),
    )

    const state = store.getState().complaint
    expect(state.fields.batch_lot_number.value).toBe('BMX240602')
    expect(state.fields.affected_quantity.value).toBe('48 capsules')
    expect(state.fields.product_name).toBe(productNameRef)
    expect(state.fields.product_strength_grade).toBe(strengthRef)
    expect(state.fields.customer_name).toBe(customerRef)
    expect(state.fields.product_name.value).toBe('Amoxicillin Capsules')
    expect(state.fields.product_strength_grade.value).toBe('500 mg')
    expect(state.fields.customer_name.value).toBe('Apollo Pharmacy')
    expect(state.recentlyUpdatedFields).toEqual([
      'batch_lot_number',
      'affected_quantity',
    ] satisfies ComplaintFieldKey[])
    expect(state.status).toBe('pending_triage')
  })

  it('applyFieldPatch does not change status by itself', () => {
    const store = createTestStore()
    store.dispatch(setComplaintStatus('needs_information'))
    store.dispatch(
      applyFieldPatch({
        changes: {
          customer_name: {
            value: 'Apollo Pharmacy',
            provenance: 'user',
            confidence: null,
            evidence: null,
          },
        },
      }),
    )

    expect(store.getState().complaint.status).toBe('needs_information')
  })

  it('resetComplaintDraft produces a fresh clean state', () => {
    const store = createTestStore()
    store.dispatch(setUserField({ field: 'customer_name', value: 'Apollo Pharmacy' }))
    store.dispatch(setComplaintStatus('processing'))

    store.dispatch(resetComplaintDraft())
    const firstReset = store.getState().complaint
    expect(firstReset).toEqual(createInitialComplaintDraftState())

    store.dispatch(setUserField({ field: 'product_name', value: 'Temp' }))
    store.dispatch(resetComplaintDraft())
    const secondReset = store.getState().complaint

    expect(secondReset).toEqual(createInitialComplaintDraftState())
    expect(secondReset.fields).not.toBe(firstReset.fields)
  })
})
