import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import Login from './Login'
import * as auth from './auth'

// Mock the auth module
vi.mock('./auth')

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('Login component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders login form with username and password fields', () => {
    // Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument()
  })

  it('submits form with username and password', async () => {
    // Arrange
    vi.mocked(auth.login).mockResolvedValue('admin')

    render(
      <MantineProvider>
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      </MantineProvider>
    )

    const usernameInput = screen.getByLabelText(/username/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /login/i })

    // Act
    fireEvent.change(usernameInput, { target: { value: 'admin' } })
    fireEvent.change(passwordInput, { target: { value: 'password' } })
    fireEvent.click(submitButton)

    // Assert
    await waitFor(() => {
      expect(auth.login).toHaveBeenCalledWith('admin', 'password')
    })
  })

  it('navigates to home page on successful login', async () => {
    // Arrange
    vi.mocked(auth.login).mockResolvedValue('admin')

    render(
      <MantineProvider>
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      </MantineProvider>
    )

    const usernameInput = screen.getByLabelText(/username/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /login/i })

    // Act
    fireEvent.change(usernameInput, { target: { value: 'admin' } })
    fireEvent.change(passwordInput, { target: { value: 'password' } })
    fireEvent.click(submitButton)

    // Assert
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/')
    })
  })

  it('displays error message on login failure', async () => {
    // Arrange
    vi.mocked(auth.login).mockRejectedValue(new Error('Login failed'))

    render(
      <MantineProvider>
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      </MantineProvider>
    )

    const usernameInput = screen.getByLabelText(/username/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /login/i })

    // Act
    fireEvent.change(usernameInput, { target: { value: 'admin' } })
    fireEvent.change(passwordInput, { target: { value: 'wrongpassword' } })
    fireEvent.click(submitButton)

    // Assert
    await waitFor(() => {
      expect(screen.getByText(/invalid username or password/i)).toBeInTheDocument()
    })
  })

  it('disables submit button while login is in progress', async () => {
    // Arrange
    vi.mocked(auth.login).mockImplementation(() => new Promise(resolve => setTimeout(() => resolve('admin'), 100)))

    render(
      <MantineProvider>
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      </MantineProvider>
    )

    const usernameInput = screen.getByLabelText(/username/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /login/i })

    // Act
    fireEvent.change(usernameInput, { target: { value: 'admin' } })
    fireEvent.change(passwordInput, { target: { value: 'password' } })
    fireEvent.click(submitButton)

    // Assert - button should be disabled during login
    expect(submitButton).toBeDisabled()
  })
})
