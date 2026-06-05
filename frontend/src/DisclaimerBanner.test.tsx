import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import DisclaimerBanner from './DisclaimerBanner'

describe('DisclaimerBanner', () => {
  it('displays educational demonstration warning', () => {
    render(
      <MantineProvider>
        <BrowserRouter>
          <DisclaimerBanner />
        </BrowserRouter>
      </MantineProvider>
    )

    expect(screen.getByText(/Educational Demonstration Only/i)).toBeInTheDocument()
  })

  it('mentions the 7-day delay explicitly', () => {
    render(
      <MantineProvider>
        <BrowserRouter>
          <DisclaimerBanner />
        </BrowserRouter>
      </MantineProvider>
    )

    expect(screen.getByText(/7\+? days?/i)).toBeInTheDocument()
  })

  it('states this is not financial advice', () => {
    render(
      <MantineProvider>
        <BrowserRouter>
          <DisclaimerBanner />
        </BrowserRouter>
      </MantineProvider>
    )

    expect(screen.getByText(/not financial advice/i)).toBeInTheDocument()
  })

  it('includes a link to the disclaimer page', () => {
    render(
      <MantineProvider>
        <BrowserRouter>
          <DisclaimerBanner />
        </BrowserRouter>
      </MantineProvider>
    )

    const link = screen.getByRole('link', { name: /disclaimer|learn more/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/disclaimer')
  })

})
