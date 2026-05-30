import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import Disclaimer from './Disclaimer'

describe('Disclaimer', () => {
  const renderDisclaimer = () => {
    return render(
      <MantineProvider>
        <BrowserRouter>
          <Disclaimer />
        </BrowserRouter>
      </MantineProvider>
    )
  }

  it('renders main heading with educational focus', () => {
    renderDisclaimer()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/educational demonstration/i)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/not financial advice/i)
  })

  it('mentions 7-day delay explicitly', () => {
    renderDisclaimer()
    expect(screen.getByText(/7[+-]day/i)).toBeInTheDocument()
  })

  it('has Important Limitations section', () => {
    renderDisclaimer()
    expect(screen.getByRole('heading', { name: /important limitations/i })).toBeInTheDocument()
  })

  it('has What This Platform Is NOT section', () => {
    renderDisclaimer()
    expect(screen.getByRole('heading', { name: /what this platform is not/i })).toBeInTheDocument()
  })

  it('includes past performance disclaimer', () => {
    renderDisclaimer()
    const matches = screen.getAllByText(/past performance.*future results/i)
    expect(matches.length).toBeGreaterThan(0)
  })

  it('recommends consulting licensed advisor', () => {
    renderDisclaimer()
    expect(screen.getByText(/consult.*licensed.*advisor/i)).toBeInTheDocument()
  })
})
