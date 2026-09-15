import { Provider } from 'react-redux'

import { store } from './app/store'

function App() {
  return (
    <Provider store={store}>
      <main>
        <h1>VeyraQ</h1>
        <p>AI-Assisted Pharmaceutical Complaint Intelligence</p>
        <p>Application foundation initialized.</p>
      </main>
    </Provider>
  )
}

export default App
