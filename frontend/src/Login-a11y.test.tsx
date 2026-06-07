import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import Login from './Login'
import * as auth from './auth'

vi.mock('./auth')

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  }
})

describe('Login — accessibility', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('announces the error message to assistive tech via role="alert" + aria-live', async () => {
    vi.mocked(auth.login).mockRejectedValue(new Error('Login failed'))

    render(
      <MantineProvider>
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      </MantineProvider>,
    )

    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'admin' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: /login/i }))

    const alert = await waitFor(() => screen.getByRole('alert'))
    expect(alert).toHaveTextContent(/invalid username or password/i)
    expect(alert).toHaveAttribute('aria-live', 'polite')
  })
})
