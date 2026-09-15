import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from './App'

describe('App', () => {
  it('renders the VeyraQ foundation shell', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: 'VeyraQ' }),
    ).toBeInTheDocument()
    expect(
      screen.getByText('AI-Assisted Pharmaceutical Complaint Intelligence'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Application foundation initialized.'),
    ).toBeInTheDocument()
  })
})
