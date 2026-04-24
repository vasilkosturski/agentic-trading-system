import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import DisclaimerBanner from './DisclaimerBanner'

describe('DisclaimerBanner', () => {
  it('displays educational demonstration warning', () => {
    // Arrange & Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <DisclaimerBanner />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    expect(screen.getByText(/Educational Demonstration Only/i)).toBeInTheDocument()
  })

  it('mentions the 7-day delay explicitly', () => {
    // Arrange & Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <DisclaimerBanner />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    expect(screen.getByText(/7\+? days?/i)).toBeInTheDocument()
  })

  it('states this is not financial advice', () => {
    // Arrange & Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <DisclaimerBanner />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    expect(screen.getByText(/not financial advice/i)).toBeInTheDocument()
  })

  it('includes a link to the disclaimer page', () => {
    // Arrange & Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <DisclaimerBanner />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    const link = screen.getByRole('link', { name: /disclaimer|learn more/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/disclaimer')
  })

  it('uses Mantine Alert component with warning styling', () => {
    // Arrange & Act
    const { container } = render(
      <MantineProvider>
        <BrowserRouter>
          <DisclaimerBanner />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert - Check for Mantine Alert component structure
    const alert = container.querySelector('[class*="Alert"]')
    expect(alert).toBeInTheDocument()
  })

  it('includes an alert icon', () => {
    // Arrange & Act
    const { container } = render(
      <MantineProvider>
        <BrowserRouter>
          <DisclaimerBanner />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert - Check for icon element
    const icon = container.querySelector('svg')
    expect(icon).toBeInTheDocument()
  })
})
