import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchRuns } from './api'
import * as auth from './auth'

// Mock auth module
vi.mock('./auth', () => ({
  getToken: vi.fn(),
  logout: vi.fn(),
}))

describe('api.ts - 403 Forbidden handling', () => {
  const originalLocation = window.location

  beforeEach(() => {
    global.fetch = vi.fn()
    localStorage.clear()
    vi.clearAllMocks()

    // Mock window.location
    delete (window as any).location
    window.location = {
      ...originalLocation,
      href: 'http://localhost:3000/',
      pathname: '/',
      search: '',
    } as Location
  })

  afterEach(() => {
    vi.restoreAllMocks()
    window.location = originalLocation
  })

  it('clears token and redirects to login when API returns 403', async () => {
    // Arrange
    vi.mocked(auth.getToken).mockReturnValue('expired.jwt.token')

    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
    } as Response)

    // Act & Assert
    await expect(fetchRuns(0, 20, undefined, true)).rejects.toThrow()

    // Verify logout was called to clear token
    expect(auth.logout).toHaveBeenCalled()

    // Verify redirect to login with returnUrl
    expect(window.location.href).toMatch(/\/login\?returnUrl=/)
  })

  it('includes current URL as returnUrl when redirecting on 403', async () => {
    // Arrange
    window.location = {
      ...originalLocation,
      href: 'http://localhost:3000/?showAll=true',
      pathname: '/',
      search: '?showAll=true',
    } as Location

    vi.mocked(auth.getToken).mockReturnValue('expired.jwt.token')

    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 403,
    } as Response)

    // Act & Assert
    await expect(fetchRuns(0, 20, undefined, true)).rejects.toThrow()

    // Verify returnUrl includes the query params
    expect(window.location.href).toContain('returnUrl=%2F%3FshowAll%3Dtrue')
  })

  it('does not clear token or redirect on other HTTP errors', async () => {
    // Arrange
    vi.mocked(auth.getToken).mockReturnValue('valid.jwt.token')

    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 500,
    } as Response)

    // Act & Assert
    await expect(fetchRuns(0, 20, undefined, true)).rejects.toThrow()

    // Verify logout was NOT called
    expect(auth.logout).not.toHaveBeenCalled()

    // Verify no redirect
    expect(window.location.href).toBe('http://localhost:3000/')
  })

  it('handles 403 from any authenticated endpoint', async () => {
    // Arrange
    vi.mocked(auth.getToken).mockReturnValue('expired.jwt.token')

    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 403,
    } as Response)

    // Act & Assert
    await expect(fetchRuns(0, 20, undefined, true)).rejects.toThrow()

    expect(auth.logout).toHaveBeenCalled()
    expect(window.location.href).toMatch(/\/login/)
  })
})
