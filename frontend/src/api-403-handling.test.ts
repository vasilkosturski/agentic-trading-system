import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchRuns } from './api'
import * as auth from './auth'
import * as navigation from './navigation'

// Mock auth module
vi.mock('./auth', () => ({
  getToken: vi.fn(),
  logout: vi.fn(),
}))

// Spy on navigation module — DO NOT replace it wholesale, we want the real
// resetNavigator/setNavigator to remain functional for other tests, but we
// want to observe navigate() calls.
vi.mock('./navigation', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./navigation')>()
  return {
    ...actual,
    navigate: vi.fn(),
  }
})

const HANG_SENTINEL = Symbol('hang')

/**
 * Race the (presumably never-resolving) promise against a small timeout.
 * If the timeout wins, the promise hung — which is the contract we want
 * for the 403 redirect path: callers' awaits never resolve, so their
 * setError(err.message) catch blocks never run, so no flash-of-error.
 */
async function raceWithTimeout<T>(
  p: Promise<T>,
  ms: number,
): Promise<T | typeof HANG_SENTINEL> {
  return Promise.race<T | typeof HANG_SENTINEL>([
    p,
    new Promise<typeof HANG_SENTINEL>((resolve) =>
      setTimeout(() => resolve(HANG_SENTINEL), ms),
    ),
  ])
}

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

  it('clears token and triggers SPA navigate to /login on 403', async () => {
    // Arrange
    vi.mocked(auth.getToken).mockReturnValue('expired.jwt.token')

    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
    } as Response)

    // Act — the promise must hang (never resolve, never reject) so callers'
    // catch blocks don't fire and paint the error before navigation completes.
    const result = await raceWithTimeout(fetchRuns(0, 20, undefined, true), 50)

    // Assert
    expect(result).toBe(HANG_SENTINEL)
    expect(auth.logout).toHaveBeenCalled()
    expect(navigation.navigate).toHaveBeenCalledWith(
      expect.stringMatching(/^\/login\?returnUrl=/),
      { replace: true },
    )
  })

  it('encodes current URL as returnUrl when redirecting on 403', async () => {
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

    // Act
    await raceWithTimeout(fetchRuns(0, 20, undefined, true), 50)

    // Assert — returnUrl includes the encoded current path + query string
    expect(navigation.navigate).toHaveBeenCalledWith(
      '/login?returnUrl=%2F%3FshowAll%3Dtrue',
      { replace: true },
    )
  })

  it('does not throw a Failed-to-fetch error visible to the caller on 403', async () => {
    // Arrange
    vi.mocked(auth.getToken).mockReturnValue('expired.jwt.token')

    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 403,
    } as Response)

    let caughtError: unknown = null
    const wrapped = fetchRuns(0, 20, undefined, true).catch((err) => {
      caughtError = err
    })

    // Wait long enough that the rejection — if any — has propagated.
    await raceWithTimeout(wrapped, 50)

    // Assert — no rejection ever surfaced to the caller's catch block.
    expect(caughtError).toBeNull()
  })

  it('does not clear token or call navigate on non-403 errors', async () => {
    // Arrange
    vi.mocked(auth.getToken).mockReturnValue('valid.jwt.token')

    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 500,
    } as Response)

    // Act & Assert — non-403 errors still throw normally.
    await expect(fetchRuns(0, 20, undefined, true)).rejects.toThrow(
      'Failed to fetch /api/runs/admin?page=0&limit=20: 500',
    )

    expect(auth.logout).not.toHaveBeenCalled()
    expect(navigation.navigate).not.toHaveBeenCalled()
  })

  it('handles 403 from any authenticated endpoint', async () => {
    // Arrange
    vi.mocked(auth.getToken).mockReturnValue('expired.jwt.token')

    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 403,
    } as Response)

    // Act
    await raceWithTimeout(fetchRuns(0, 20, undefined, true), 50)

    // Assert
    expect(auth.logout).toHaveBeenCalled()
    expect(navigation.navigate).toHaveBeenCalledWith(
      expect.stringMatching(/^\/login/),
      { replace: true },
    )
  })
})
