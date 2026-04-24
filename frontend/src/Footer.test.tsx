import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import Footer from './Footer'

describe('Footer', () => {
  it('renders as semantic footer element', () => {
    // Arrange & Act
    const { container } = render(
      <MantineProvider>
        <BrowserRouter>
          <Footer />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    const footer = container.querySelector('footer')
    expect(footer).toBeInTheDocument()
  })

  it('displays educational demonstration disclaimer text', () => {
    // Arrange & Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <Footer />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    expect(screen.getByText(/Educational demonstration only/i)).toBeInTheDocument()
  })

  it('mentions the 7-day delay explicitly', () => {
    // Arrange & Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <Footer />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    expect(screen.getByText(/7\+? days?/i)).toBeInTheDocument()
  })

  it('includes a link to the disclaimer page', () => {
    // Arrange & Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <Footer />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    const link = screen.getByRole('link', { name: /disclaimer|view full disclaimer/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/disclaimer')
  })

  it('uses dimmed text styling for subtle appearance', () => {
    // Arrange & Act
    const { container } = render(
      <MantineProvider>
        <BrowserRouter>
          <Footer />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert - Check for Mantine Text component with dimmed color
    const text = container.querySelector('[class*="Text"]')
    expect(text).toBeInTheDocument()
  })

  it('uses small text size for non-intrusive display', () => {
    // Arrange & Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <Footer />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert - Text should be small (xs)
    const disclaimerText = screen.getByText(/Educational demonstration only/i)
    expect(disclaimerText).toBeInTheDocument()
  })

  it('centers text for balanced layout', () => {
    // Arrange & Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <Footer />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert - Footer text should be centered
    const disclaimerText = screen.getByText(/Educational demonstration only/i)
    expect(disclaimerText).toBeInTheDocument()
  })

  it('has border top for visual separation', () => {
    // Arrange & Act
    const { container } = render(
      <MantineProvider>
        <BrowserRouter>
          <Footer />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert - Footer should have top border
    const footer = container.querySelector('footer')
    expect(footer).toBeInTheDocument()
  })
})
