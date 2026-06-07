import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchRuns } from './api'
import * as auth from '@/features/auth/auth'
import * as navigation from './navigation'

vi.mock('@/features/auth/auth', () => ({
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

describe('api.ts — fetchRuns with showAll parameter (public vs admin endpoint)', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('calls /api/runs endpoint when showAll is false', async () => {
    const mockResponse = {
      runs: [{ runId: '123', agentId: 1, status: 'COMPLETED' }],
      total: 104,
      page: 0,
      limit: 20,
    }

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    await fetchRuns(0, 20, undefined, false)

    expect(global.fetch).toHaveBeenCalledWith('/api/runs?page=0&limit=20', {})
    expect(global.fetch).toHaveBeenCalledTimes(1)
  })

  it('calls /api/runs/admin endpoint when showAll is true', async () => {
    const mockResponse = {
      runs: [
        { runId: '1', agentId: 1, status: 'COMPLETED' },
        { runId: '2', agentId: 2, status: 'IN_PROGRESS' },
      ],
      total: 188,
      page: 0,
      limit: 20,
    }

    vi.mocked(auth.getToken).mockReturnValue('test.jwt.token')

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    await fetchRuns(0, 20, undefined, true)

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/runs/admin?page=0&limit=20',
      expect.objectContaining({
        headers: expect.objectContaining({
          'Authorization': 'Bearer test.jwt.token',
        }),
      }),
    )
    expect(global.fetch).toHaveBeenCalledTimes(1)
  })

  it('passes AbortSignal through to fetch', async () => {
    const mockResponse = { runs: [], total: 188, page: 1, limit: 10 }

    vi.mocked(auth.getToken).mockReturnValue('test.jwt.token')

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    const abortController = new AbortController()

    await fetchRuns(1, 10, abortController.signal, true)

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/runs/admin?page=1&limit=10',
      expect.objectContaining({
        signal: abortController.signal,
        headers: expect.objectContaining({
          'Authorization': 'Bearer test.jwt.token',
        }),
      }),
    )
  })

  it('returns paginated runs data structure from admin endpoint', async () => {
    const mockResponse = {
      runs: [
        { runId: '1', agentId: 1, status: 'COMPLETED' },
        { runId: '2', agentId: 2, status: 'IN_PROGRESS' },
      ],
      total: 188,
      page: 0,
      limit: 20,
    }

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    const result = await fetchRuns(0, 20, undefined, true)

    expect(result).toEqual(mockResponse)
  })

  it('throws on non-403 failure (e.g., 401)', async () => {
    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 401,
    } as Response)

    await expect(fetchRuns(0, 20, undefined, true)).rejects.toThrow(
      'Failed to fetch /api/runs/admin?page=0&limit=20: 401',
    )
  })
})

describe('api.ts — JWT Authorization header presence', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('omits Authorization header for public endpoint (no token in request)', async () => {
    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ runs: [], total: 0, page: 0, limit: 20 }),
    } as Response)

    await fetchRuns(0, 20, undefined, false)

    const options = vi.mocked(global.fetch).mock.calls[0][1] as RequestInit | undefined
    const headers = options?.headers as Record<string, string> | undefined
    expect(headers?.Authorization).toBeUndefined()
  })

  it('omits Authorization header on admin endpoint when no token is stored', async () => {
    vi.mocked(auth.getToken).mockReturnValue(null)
    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ runs: [], total: 0, page: 0, limit: 20 }),
    } as Response)

    await fetchRuns(0, 20, undefined, true)

    const options = vi.mocked(global.fetch).mock.calls[0][1] as RequestInit | undefined
    const headers = options?.headers as Record<string, string> | undefined
    expect(headers?.Authorization).toBeUndefined()
  })
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

describe('api.ts — 403 Forbidden handling', () => {
  const originalLocation = window.location

  beforeEach(() => {
    global.fetch = vi.fn()
    localStorage.clear()
    vi.clearAllMocks()

    delete (window as Partial<Window>).location
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
    vi.mocked(auth.getToken).mockReturnValue('expired.jwt.token')

    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
    } as Response)

    const result = await raceWithTimeout(fetchRuns(0, 20, undefined, true), 50)

    expect(result).toBe(HANG_SENTINEL)
    expect(auth.logout).toHaveBeenCalled()
    expect(navigation.navigate).toHaveBeenCalledWith(
      expect.stringMatching(/^\/login\?returnUrl=/),
      { replace: true },
    )
  })

  it('encodes current URL as returnUrl when redirecting on 403', async () => {
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

    await raceWithTimeout(fetchRuns(0, 20, undefined, true), 50)

    expect(navigation.navigate).toHaveBeenCalledWith(
      '/login?returnUrl=%2F%3FshowAll%3Dtrue',
      { replace: true },
    )
  })

  it('does not throw a Failed-to-fetch error visible to the caller on 403', async () => {
    vi.mocked(auth.getToken).mockReturnValue('expired.jwt.token')

    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 403,
    } as Response)

    let caughtError: unknown = null
    const wrapped = fetchRuns(0, 20, undefined, true).catch((err) => {
      caughtError = err
    })

    await raceWithTimeout(wrapped, 50)

    expect(caughtError).toBeNull()
  })

  it('does not clear token or call navigate on non-403 errors', async () => {
    vi.mocked(auth.getToken).mockReturnValue('valid.jwt.token')

    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 500,
    } as Response)

    await expect(fetchRuns(0, 20, undefined, true)).rejects.toThrow(
      'Failed to fetch /api/runs/admin?page=0&limit=20: 500',
    )

    expect(auth.logout).not.toHaveBeenCalled()
    expect(navigation.navigate).not.toHaveBeenCalled()
  })
})
