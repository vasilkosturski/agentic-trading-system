import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchRuns } from './api'
import * as auth from './auth'

vi.mock('./auth')

describe('api.ts - JWT token integration', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('includes Authorization header with JWT token for admin endpoint', async () => {
    const mockResponse = {
      runs: [],
      total: 0,
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
          'Authorization': 'Bearer test.jwt.token'
        })
      })
    )
  })

  it('does not include Authorization header for public endpoint', async () => {
    const mockResponse = {
      runs: [],
      total: 0,
      page: 0,
      limit: 20,
    }

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    await fetchRuns(0, 20, undefined, false)

    const fetchCall = vi.mocked(global.fetch).mock.calls[0]
    const options = fetchCall[1] as RequestInit | undefined

    expect(
      !options ||
      !options.headers ||
      !(options.headers as Record<string, string>)['Authorization']
    ).toBe(true)
  })

  it('includes Authorization header even with AbortSignal', async () => {
    const mockResponse = {
      runs: [],
      total: 0,
      page: 0,
      limit: 20,
    }

    vi.mocked(auth.getToken).mockReturnValue('test.jwt.token')

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    const abortController = new AbortController()

    await fetchRuns(0, 20, abortController.signal, true)

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/runs/admin?page=0&limit=20',
      expect.objectContaining({
        signal: abortController.signal,
        headers: expect.objectContaining({
          'Authorization': 'Bearer test.jwt.token'
        })
      })
    )
  })

  it('omits Authorization header when no token is stored', async () => {
    const mockResponse = {
      runs: [],
      total: 0,
      page: 0,
      limit: 20,
    }

    vi.mocked(auth.getToken).mockReturnValue(null)

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    await fetchRuns(0, 20, undefined, true)

    const fetchCall = vi.mocked(global.fetch).mock.calls[0]
    const options = fetchCall[1] as RequestInit | undefined

    expect(
      !options?.headers ||
      !(options.headers as Record<string, string>)['Authorization']
    ).toBe(true)
  })
})
