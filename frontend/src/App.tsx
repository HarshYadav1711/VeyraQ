import { Provider } from 'react-redux'

import { store } from './app/store'
import { ComplaintWorkspace } from './features/complaint/components/ComplaintWorkspace'

function App() {
  return (
    <Provider store={store}>
      <ComplaintWorkspace />
    </Provider>
  )
}

export default App
