import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

import {
  createInitialComplaintDraftState,
  type ComplaintFieldKey,
  type ComplaintFieldValue,
  type ComplaintPatch,
  type ComplaintStatus,
} from './complaintTypes'

interface SetUserFieldPayload {
  field: ComplaintFieldKey
  value: string | null
}

const complaintSlice = createSlice({
  name: 'complaint',
  initialState: createInitialComplaintDraftState(),
  reducers: {
    setUserField(state, action: PayloadAction<SetUserFieldPayload>) {
      const { field, value } = action.payload
      state.fields[field] = {
        value,
        provenance: 'user',
        confidence: null,
        evidence: null,
      }
      if (!state.recentlyUpdatedFields.includes(field)) {
        state.recentlyUpdatedFields.push(field)
      }
    },

    applyFieldPatch(state, action: PayloadAction<ComplaintPatch>) {
      const changedKeys: ComplaintFieldKey[] = []
      for (const [key, fieldValue] of Object.entries(action.payload.changes) as [
        ComplaintFieldKey,
        ComplaintFieldValue,
      ][]) {
        if (fieldValue === undefined) {
          continue
        }
        state.fields[key] = {
          value: fieldValue.value,
          provenance: fieldValue.provenance,
          confidence: fieldValue.confidence,
          evidence: fieldValue.evidence,
        }
        changedKeys.push(key)
      }
      state.recentlyUpdatedFields = changedKeys
    },

    setComplaintStatus(state, action: PayloadAction<ComplaintStatus>) {
      state.status = action.payload
    },

    clearRecentlyUpdatedFields(state) {
      state.recentlyUpdatedFields = []
    },

    resetComplaintDraft() {
      return createInitialComplaintDraftState()
    },
  },
})

export const {
  setUserField,
  applyFieldPatch,
  setComplaintStatus,
  clearRecentlyUpdatedFields,
  resetComplaintDraft,
} = complaintSlice.actions

export default complaintSlice.reducer
