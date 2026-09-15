import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from './App'

describe('App', () => {
  it('renders the complaint workspace shell', () => {
    render(<App />)

    expect(screen.getByText('VeyraQ')).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Log Customer Complaint' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'VeyraQ Assistant' }),
    ).toBeInTheDocument()
  })
})
