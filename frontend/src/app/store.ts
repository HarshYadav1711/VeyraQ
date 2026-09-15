import { configureStore } from '@reduxjs/toolkit'

import assistantReducer from '../features/assistant/assistantSlice'
import complaintReducer from '../features/complaint/complaintSlice'

export const store = configureStore({
  reducer: {
    complaint: complaintReducer,
    assistant: assistantReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
