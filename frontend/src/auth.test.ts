import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { login, logout, getToken, isAuthenticated } from './auth'

describe('auth.ts - JWT authentication utilities', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
    // Setup fetch mock
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('login calls /api/auth/login with credentials', async () => {
    // Arrange
    const mockResponse = {
      token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token',
      username: 'admin'
    }

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    // Act
    await login('admin', 'password')

    // Assert
    expect(global.fetch).toHaveBeenCalledWith('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: 'password' })
    })
  })

  it('login stores JWT token in localStorage on success', async () => {
    // Arrange
    const mockResponse = {
      token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token',
      username: 'admin'
    }

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    // Act
    await login('admin', 'password')

    // Assert
    expect(localStorage.getItem('jwt_token')).toBe('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token')
  })

  it('login returns username on success', async () => {
    // Arrange
    const mockResponse = {
      token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token',
      username: 'admin'
    }

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    // Act
    const username = await login('admin', 'password')

    // Assert
    expect(username).toBe('admin')
  })

  it('login throws error on invalid credentials', async () => {
    // Arrange
    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 401,
    } as Response)

    // Act & Assert
    await expect(login('admin', 'wrongpassword')).rejects.toThrow('Login failed')
  })

  it('logout removes token from localStorage', () => {
    // Arrange
    localStorage.setItem('jwt_token', 'test.token.value')

    // Act
    logout()

    // Assert
    expect(localStorage.getItem('jwt_token')).toBeNull()
  })

  it('getToken returns token from localStorage', () => {
    // Arrange
    localStorage.setItem('jwt_token', 'test.token.value')

    // Act
    const token = getToken()

    // Assert
    expect(token).toBe('test.token.value')
  })

  it('getToken returns null when no token stored', () => {
    // Act
    const token = getToken()

    // Assert
    expect(token).toBeNull()
  })

  it('isAuthenticated returns true when token exists', () => {
    // Arrange
    localStorage.setItem('jwt_token', 'test.token.value')

    // Act
    const authenticated = isAuthenticated()

    // Assert
    expect(authenticated).toBe(true)
  })

  it('isAuthenticated returns false when no token exists', () => {
    // Act
    const authenticated = isAuthenticated()

    // Assert
    expect(authenticated).toBe(false)
  })
})
