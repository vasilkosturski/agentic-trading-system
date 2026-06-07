import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import AppLayout from './AppLayout'

describe('AppLayout', () => {
  it('renders the disclaimer banner before all content', () => {
    const { container } = render(
      <MantineProvider>
        <BrowserRouter>
          <AppLayout>
            <div>Test Content</div>
          </AppLayout>
        </BrowserRouter>
      </MantineProvider>
    )

    const alert = container.querySelector('[role="alert"]')
    expect(alert).toBeInTheDocument()
    expect(alert?.textContent).toMatch(/Educational Demonstration Only/i)
    expect(screen.getByText('Test Content')).toBeInTheDocument()
  })

  it('renders the footer after all content', () => {
    const { container } = render(
      <MantineProvider>
        <BrowserRouter>
          <AppLayout>
            <div>Test Content</div>
          </AppLayout>
        </BrowserRouter>
      </MantineProvider>
    )

    const footer = container.querySelector('footer')
    expect(footer).toBeInTheDocument()
    const footerText = footer?.textContent
    expect(footerText).toMatch(/Educational demonstration only/i)
    expect(footerText).toMatch(/7\+? days?/i)
  })
})
