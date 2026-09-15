import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit'

import {
  applyFieldPatch,
  resetComplaintDraft,
  setComplaintStatus,
} from '../complaint/complaintSlice'
import type { ComplaintDraftState } from '../complaint/complaintTypes'
import { AssistantApiError, postAssistantProcess } from './assistantApi'
import {
  createAssistantMessageId,
  createInitialAssistantState,
  type AssistantMessage,
  type AssistantState,
} from './assistantTypes'

interface RootSliceState {
  complaint: ComplaintDraftState
  assistant: AssistantState
}

interface ProcessAssistantArgs {
  message: string
  retry?: boolean
}

const SAFE_UNAVAILABLE =
  'AI processing is temporarily unavailable. Your complaint draft has not been changed.'

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
      dispatch(applyFieldPatch(response.patch))
      dispatch(setComplaintStatus(response.status))
      dispatch(
        addAssistantMessage({
          id: createAssistantMessageId(),
          role: 'assistant',
          content: response.assistant_message,
        }),
      )
    } catch (error) {
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
    clearAssistantError(state) {
      state.error = null
      if (state.requestStatus === 'failed') {
        state.requestStatus = 'idle'
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
        state.requestStatus = 'failed'
        state.error = action.payload ?? SAFE_UNAVAILABLE
        state.statusBeforeProcessing = null
      })
      .addCase(resetComplaintDraft, () => createInitialAssistantState())
  },
})

export const {
  addUserMessage,
  addAssistantMessage,
  rememberStatusBeforeProcessing,
  clearAssistantError,
  resetAssistant,
} = assistantSlice.actions

export default assistantSlice.reducer
