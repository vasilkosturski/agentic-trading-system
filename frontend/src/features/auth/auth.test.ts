import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { login, logout, getToken, isAuthenticated } from './auth'

describe('auth.ts - JWT authentication utilities', () => {
  beforeEach(() => {
    localStorage.clear()
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('login calls /api/auth/login with credentials', async () => {
    const mockResponse = {
      token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token',
      username: 'admin'
    }

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    await login('admin', 'password')

    expect(global.fetch).toHaveBeenCalledWith('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: 'password' })
    })
  })

  it('login stores JWT token in localStorage on success', async () => {
    const mockResponse = {
      token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token',
      username: 'admin'
    }

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    await login('admin', 'password')

    expect(localStorage.getItem('jwt_token')).toBe('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token')
  })

  it('login returns username on success', async () => {
    const mockResponse = {
      token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token',
      username: 'admin'
    }

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    const username = await login('admin', 'password')

    expect(username).toBe('admin')
  })

  it('login throws error on invalid credentials', async () => {
    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 401,
    } as Response)

    await expect(login('admin', 'wrongpassword')).rejects.toThrow('Login failed')
  })

  it('logout removes token from localStorage', () => {
    localStorage.setItem('jwt_token', 'test.token.value')

    logout()

    expect(localStorage.getItem('jwt_token')).toBeNull()
  })

  it('getToken returns token from localStorage', () => {
    localStorage.setItem('jwt_token', 'test.token.value')

    const token = getToken()

    expect(token).toBe('test.token.value')
  })

  it('getToken returns null when no token stored', () => {
    const token = getToken()

    expect(token).toBeNull()
  })

  it('isAuthenticated returns true when token exists', () => {
    localStorage.setItem('jwt_token', 'test.token.value')

    const authenticated = isAuthenticated()

    expect(authenticated).toBe(true)
  })

  it('isAuthenticated returns false when no token exists', () => {
    const authenticated = isAuthenticated()

    expect(authenticated).toBe(false)
  })
})
