import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import DisclaimerBanner from './DisclaimerBanner'
import { assertDisclaimerSemantics } from '@/test/disclaimer-assertions'

function renderBanner() {
  return render(
    <MantineProvider>
      <BrowserRouter>
        <DisclaimerBanner />
      </BrowserRouter>
    </MantineProvider>,
  )
}

describe('DisclaimerBanner', () => {
  it('communicates the educational-only framing, 7-day delay, and disclaimer link', () => {
    const { container } = renderBanner()
    assertDisclaimerSemantics(container)
  })

  it('states explicitly that this is not financial advice', () => {
    renderBanner()
    expect(screen.getByText(/not financial advice/i)).toBeInTheDocument()
  })
})
