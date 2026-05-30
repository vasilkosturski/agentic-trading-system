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

})
