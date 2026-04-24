import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import AppLayout from './AppLayout'

describe('AppLayout', () => {
  it('renders the disclaimer banner before all content', () => {
    // Arrange & Act
    const { container } = render(
      <MantineProvider>
        <BrowserRouter>
          <AppLayout>
            <div>Test Content</div>
          </AppLayout>
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert - Banner should be in alert role
    const alert = container.querySelector('[role="alert"]')
    expect(alert).toBeInTheDocument()
    expect(alert?.textContent).toMatch(/Educational Demonstration Only/i)
    expect(screen.getByText('Test Content')).toBeInTheDocument()
  })

  it('wraps content in a Container', () => {
    // Arrange & Act
    const { container } = render(
      <MantineProvider>
        <BrowserRouter>
          <AppLayout>
            <div>Test Content</div>
          </AppLayout>
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert - Check for Mantine Container
    const mantineContainer = container.querySelector('[class*="Container"]')
    expect(mantineContainer).toBeInTheDocument()
  })

  it('displays banner on all routes', () => {
    // Arrange & Act
    const { container } = render(
      <MantineProvider>
        <BrowserRouter>
          <Routes>
            <Route path="*" element={
              <AppLayout>
                <div>Any Route</div>
              </AppLayout>
            } />
          </Routes>
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert - Banner should be in alert role
    const alert = container.querySelector('[role="alert"]')
    expect(alert).toBeInTheDocument()
    expect(alert?.textContent).toMatch(/Educational Demonstration Only/i)
  })

  it('renders the footer after all content', () => {
    // Arrange & Act
    const { container } = render(
      <MantineProvider>
        <BrowserRouter>
          <AppLayout>
            <div>Test Content</div>
          </AppLayout>
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    const footer = container.querySelector('footer')
    expect(footer).toBeInTheDocument()
    // Check footer contains the disclaimer text
    const footerText = footer?.textContent
    expect(footerText).toMatch(/Educational demonstration only/i)
    expect(footerText).toMatch(/7\+? days?/i)
  })

  it('footer includes link to disclaimer page', () => {
    // Arrange & Act
    const { container } = render(
      <MantineProvider>
        <BrowserRouter>
          <AppLayout>
            <div>Test Content</div>
          </AppLayout>
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert - Footer should have disclaimer link
    const footer = container.querySelector('footer')
    const footerLink = footer?.querySelector('a[href="/disclaimer"]')
    expect(footerLink).toBeInTheDocument()
    expect(footerLink?.textContent).toMatch(/disclaimer/i)
  })

  it('footer appears on all routes', () => {
    // Arrange & Act
    const { container } = render(
      <MantineProvider>
        <BrowserRouter>
          <Routes>
            <Route path="*" element={
              <AppLayout>
                <div>Any Route</div>
              </AppLayout>
            } />
          </Routes>
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    const footer = container.querySelector('footer')
    expect(footer).toBeInTheDocument()
  })
})
