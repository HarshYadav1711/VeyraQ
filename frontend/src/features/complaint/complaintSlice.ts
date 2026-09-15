import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit'

import { ComplaintApiError, postCommitComplaint } from './complaintApi'
import {
  createInitialComplaintDraftState,
  serializeCommitRequest,
  type ComplaintDraftState,
  type ComplaintFieldKey,
  type ComplaintFieldValue,
  type ComplaintPatch,
  type ComplaintStatus,
  type CommittedComplaintResponse,
} from './complaintTypes'

interface SetUserFieldPayload {
  field: ComplaintFieldKey
  value: string | null
}

export const commitComplaint = createAsyncThunk<
  CommittedComplaintResponse,
  void,
  { state: { complaint: ComplaintDraftState }; rejectValue: string }
>('complaint/commit', async (_, { getState, rejectWithValue }) => {
  const { fields, status } = getState().complaint
  if (status !== 'ready_to_commit') {
    return rejectWithValue(
      'Complaint must be ready for review before it can be committed.',
    )
  }

  try {
    return await postCommitComplaint(serializeCommitRequest(fields))
  } catch (error) {
    if (error instanceof ComplaintApiError) {
      return rejectWithValue(error.message)
    }
    return rejectWithValue('Unable to commit complaint. Please try again.')
  }
})

const complaintSlice = createSlice({
  name: 'complaint',
  initialState: createInitialComplaintDraftState(),
  reducers: {
    setUserField(state, action: PayloadAction<SetUserFieldPayload>) {
      if (state.status === 'committed') {
        return
      }
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
      if (state.status === 'committed') {
        return
      }
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

    clearCommitError(state) {
      state.commitError = null
      if (state.commitStatus === 'failed') {
        state.commitStatus = 'idle'
      }
    },

    resetComplaintDraft() {
      return createInitialComplaintDraftState()
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(commitComplaint.pending, (state) => {
        state.commitStatus = 'submitting'
        state.commitError = null
      })
      .addCase(commitComplaint.fulfilled, (state, action) => {
        state.commitStatus = 'succeeded'
        state.commitError = null
        state.status = 'committed'
        state.committedRecordId = action.payload.id
        state.complaintNumber = action.payload.complaint_number
        state.fields = action.payload.fields
        state.recentlyUpdatedFields = []
      })
      .addCase(commitComplaint.rejected, (state, action) => {
        state.commitStatus = 'failed'
        state.commitError =
          action.payload ?? 'Unable to commit complaint. Please try again.'
      })
  },
})

export const {
  setUserField,
  applyFieldPatch,
  setComplaintStatus,
  clearRecentlyUpdatedFields,
  clearCommitError,
  resetComplaintDraft,
} = complaintSlice.actions

export default complaintSlice.reducer
