import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import Footer from './Footer'
import { assertDisclaimerSemantics } from './test/disclaimer-assertions'

function renderFooter() {
  return render(
    <MantineProvider>
      <BrowserRouter>
        <Footer />
      </BrowserRouter>
    </MantineProvider>,
  )
}

describe('Footer', () => {
  it('renders as semantic footer element', () => {
    const { container } = renderFooter()
    expect(container.querySelector('footer')).toBeInTheDocument()
  })

  it('communicates the educational-only framing, 7-day delay, and disclaimer link', () => {
    const { container } = renderFooter()
    assertDisclaimerSemantics(container)
  })
})
