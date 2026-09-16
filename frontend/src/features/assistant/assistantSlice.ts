import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit'

import {
  applyFieldPatch,
  resetComplaintDraft,
  setComplaintStatus,
  setUserField,
} from '../complaint/complaintSlice'
import type { ComplaintDraftState } from '../complaint/complaintTypes'
import {
  AssistantApiError,
  postAssistantProcess,
  postInvestigationAssistance,
  processComplaintDocument,
} from './assistantApi'
import {
  createAssistantMessageId,
  createInitialAssistantState,
  DISCARDED_REQUEST,
  type AssistantMessage,
  type AssistantState,
  type InvestigationAssistance,
  type RelatedComplaintMatch,
} from './assistantTypes'

interface RootSliceState {
  complaint: ComplaintDraftState
  assistant: AssistantState
}

interface ProcessAssistantArgs {
  message: string
  retry?: boolean
}

interface ProcessDocumentArgs {
  file: File
  displayName: string
}

const SAFE_UNAVAILABLE =
  'AI processing is temporarily unavailable. Your complaint draft has not been changed.'

const SAFE_INVESTIGATION_UNAVAILABLE =
  'Investigation assistance is temporarily unavailable. Your complaint record has not been changed.'

function clearInvestigationState(state: AssistantState) {
  state.investigationAssistance = null
  state.investigationError = null
  if (state.investigationStatus !== 'processing') {
    state.investigationStatus = 'idle'
  }
}

function isCurrentGeneration(
  getState: () => RootSliceState,
  generation: number,
): boolean {
  return getState().assistant.requestGeneration === generation
}

export const processAssistantMessage = createAsyncThunk<
  void,
  ProcessAssistantArgs,
  { state: RootSliceState; rejectValue: string }
>(
  'assistant/process',
  async ({ message, retry }, { getState, dispatch, rejectWithValue }) => {
    const trimmed = message.trim()
    if (!trimmed) {
      return rejectWithValue('Enter a complaint or correction before sending.')
    }

    const { complaint, assistant } = getState()
    if (complaint.status === 'committed') {
      return rejectWithValue(
        'This complaint is already committed. Start a New Complaint to continue.',
      )
    }

    if (!retry) {
      dispatch(
        addUserMessage({
          id: createAssistantMessageId(),
          role: 'user',
          content: trimmed,
        }),
      )
    }

    const generation = assistant.requestGeneration
    const previousStatus =
      complaint.status === 'processing'
        ? (assistant.statusBeforeProcessing ?? 'pending_triage')
        : complaint.status
    dispatch(rememberStatusBeforeProcessing(previousStatus))
    dispatch(setComplaintStatus('processing'))

    try {
      const response = await postAssistantProcess({
        message: trimmed,
        fields: complaint.fields,
      })
      if (!isCurrentGeneration(getState, generation)) {
        return rejectWithValue(DISCARDED_REQUEST)
      }
      dispatch(applyFieldPatch(response.patch))
      dispatch(setComplaintStatus(response.status))
      if (response.related_lookup_evaluated) {
        dispatch(
          setRelatedComplaints({
            matches: response.related_complaints ?? [],
            evaluated: true,
          }),
        )
      }
      dispatch(
        addAssistantMessage({
          id: createAssistantMessageId(),
          role: 'assistant',
          content: response.assistant_message,
        }),
      )
    } catch (error) {
      if (!isCurrentGeneration(getState, generation)) {
        return rejectWithValue(DISCARDED_REQUEST)
      }
      dispatch(setComplaintStatus(previousStatus))
      if (error instanceof AssistantApiError) {
        return rejectWithValue(
          error.status >= 500 ? SAFE_UNAVAILABLE : error.message,
        )
      }
      return rejectWithValue(SAFE_UNAVAILABLE)
    }
  },
  {
    condition: (_, { getState }) =>
      getState().assistant.requestStatus !== 'processing',
  },
)

export const processAssistantDocument = createAsyncThunk<
  void,
  ProcessDocumentArgs,
  { state: RootSliceState; rejectValue: string }
>(
  'assistant/processDocument',
  async ({ file, displayName }, { getState, dispatch, rejectWithValue }) => {
    const { complaint, assistant } = getState()
    if (complaint.status === 'committed') {
      return rejectWithValue(
        'This complaint is already committed. Start a New Complaint to continue.',
      )
    }

    dispatch(
      addUserMessage({
        id: createAssistantMessageId(),
        role: 'user',
        content: `Uploaded complaint document: ${displayName}`,
      }),
    )

    const generation = assistant.requestGeneration
    const previousStatus =
      complaint.status === 'processing'
        ? (assistant.statusBeforeProcessing ?? 'pending_triage')
        : complaint.status
    dispatch(rememberStatusBeforeProcessing(previousStatus))
    dispatch(setComplaintStatus('processing'))

    try {
      const response = await processComplaintDocument(file, complaint.fields)
      if (!isCurrentGeneration(getState, generation)) {
        return rejectWithValue(DISCARDED_REQUEST)
      }
      dispatch(applyFieldPatch(response.patch))
      dispatch(setComplaintStatus(response.status))
      if (response.related_lookup_evaluated) {
        dispatch(
          setRelatedComplaints({
            matches: response.related_complaints ?? [],
            evaluated: true,
          }),
        )
      }
      dispatch(
        addAssistantMessage({
          id: createAssistantMessageId(),
          role: 'assistant',
          content: response.assistant_message,
        }),
      )
    } catch (error) {
      if (!isCurrentGeneration(getState, generation)) {
        return rejectWithValue(DISCARDED_REQUEST)
      }
      dispatch(setComplaintStatus(previousStatus))
      if (error instanceof AssistantApiError) {
        return rejectWithValue(
          error.status >= 500 ? SAFE_UNAVAILABLE : error.message,
        )
      }
      return rejectWithValue(SAFE_UNAVAILABLE)
    }
  },
  {
    condition: (_, { getState }) =>
      getState().assistant.requestStatus !== 'processing',
  },
)

export const generateInvestigationAssistance = createAsyncThunk<
  InvestigationAssistance,
  void,
  { state: RootSliceState; rejectValue: string }
>(
  'assistant/investigation',
  async (_, { getState, rejectWithValue }) => {
    const { complaint, assistant } = getState()
    const product = complaint.fields.product_name.value?.trim()
    const description = complaint.fields.complaint_description.value?.trim()
    if (!product || !description) {
      return rejectWithValue(
        'Product Name and Complaint Description are required before investigation assistance can be generated.',
      )
    }

    const generation = assistant.requestGeneration

    try {
      const result = await postInvestigationAssistance(complaint.fields)
      if (!isCurrentGeneration(getState, generation)) {
        return rejectWithValue(DISCARDED_REQUEST)
      }
      return result
    } catch (error) {
      if (!isCurrentGeneration(getState, generation)) {
        return rejectWithValue(DISCARDED_REQUEST)
      }
      if (error instanceof AssistantApiError) {
        return rejectWithValue(
          error.status >= 500 ? SAFE_INVESTIGATION_UNAVAILABLE : error.message,
        )
      }
      return rejectWithValue(SAFE_INVESTIGATION_UNAVAILABLE)
    }
  },
  {
    condition: (_, { getState }) =>
      getState().assistant.investigationStatus !== 'processing',
  },
)

const assistantSlice = createSlice({
  name: 'assistant',
  initialState: createInitialAssistantState(),
  reducers: {
    addUserMessage(state, action: PayloadAction<AssistantMessage>) {
      state.messages.push(action.payload)
    },
    addAssistantMessage(state, action: PayloadAction<AssistantMessage>) {
      state.messages.push(action.payload)
    },
    rememberStatusBeforeProcessing(
      state,
      action: PayloadAction<AssistantState['statusBeforeProcessing']>,
    ) {
      state.statusBeforeProcessing = action.payload
    },
    setRelatedComplaints(
      state,
      action: PayloadAction<{
        matches: RelatedComplaintMatch[]
        evaluated: boolean
      }>,
    ) {
      state.relatedComplaints = action.payload.matches
      state.relatedLookupEvaluated = action.payload.evaluated
      // Related-history context changed — prior investigation is stale.
      clearInvestigationState(state)
    },
    clearAssistantError(state) {
      state.error = null
      if (state.requestStatus === 'failed') {
        state.requestStatus = 'idle'
      }
    },
    clearInvestigationError(state) {
      state.investigationError = null
      if (state.investigationStatus === 'failed') {
        state.investigationStatus = 'idle'
      }
    },
    resetAssistant() {
      return createInitialAssistantState()
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(processAssistantMessage.pending, (state) => {
        state.requestStatus = 'processing'
        state.error = null
      })
      .addCase(processAssistantMessage.fulfilled, (state) => {
        state.requestStatus = 'idle'
        state.error = null
        state.statusBeforeProcessing = null
      })
      .addCase(processAssistantMessage.rejected, (state, action) => {
        if (action.payload === DISCARDED_REQUEST) {
          return
        }
        state.requestStatus = 'failed'
        state.error = action.payload ?? SAFE_UNAVAILABLE
        state.statusBeforeProcessing = null
      })
      .addCase(processAssistantDocument.pending, (state) => {
        state.requestStatus = 'processing'
        state.error = null
      })
      .addCase(processAssistantDocument.fulfilled, (state) => {
        state.requestStatus = 'idle'
        state.error = null
        state.statusBeforeProcessing = null
      })
      .addCase(processAssistantDocument.rejected, (state, action) => {
        if (action.payload === DISCARDED_REQUEST) {
          return
        }
        state.requestStatus = 'failed'
        state.error = action.payload ?? SAFE_UNAVAILABLE
        state.statusBeforeProcessing = null
      })
      .addCase(generateInvestigationAssistance.pending, (state) => {
        state.investigationStatus = 'processing'
        state.investigationError = null
      })
      .addCase(generateInvestigationAssistance.fulfilled, (state, action) => {
        state.investigationStatus = 'ready'
        state.investigationError = null
        state.investigationAssistance = action.payload
      })
      .addCase(generateInvestigationAssistance.rejected, (state, action) => {
        if (action.payload === DISCARDED_REQUEST) {
          return
        }
        state.investigationStatus = 'failed'
        state.investigationError =
          action.payload ?? SAFE_INVESTIGATION_UNAVAILABLE
      })
      .addCase(setUserField, (state) => {
        clearInvestigationState(state)
      })
      .addCase(applyFieldPatch, (state) => {
        clearInvestigationState(state)
      })
      .addCase(resetComplaintDraft, (state) =>
        createInitialAssistantState(state.requestGeneration + 1),
      )
  },
})

export const {
  addUserMessage,
  addAssistantMessage,
  rememberStatusBeforeProcessing,
  setRelatedComplaints,
  clearAssistantError,
  clearInvestigationError,
  resetAssistant,
} = assistantSlice.actions

export default assistantSlice.reducer
