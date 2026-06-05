import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchRuns } from './api'
import * as auth from './auth'

vi.mock('./auth')

describe('api.ts - fetchRuns with showAll parameter for admin endpoint', () => {
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
          'Authorization': 'Bearer test.jwt.token'
        })
      })
    )
    expect(global.fetch).toHaveBeenCalledTimes(1)
  })

  it('accepts showAll with AbortSignal', async () => {
    const mockResponse = {
      runs: [],
      total: 188,
      page: 1,
      limit: 10,
    }

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
          'Authorization': 'Bearer test.jwt.token'
        })
      })
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
    expect(result.runs).toHaveLength(2)
    expect(result.total).toBe(188)
  })

  it('throws error when admin endpoint fetch fails', async () => {
    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 401,
    } as Response)

    await expect(fetchRuns(0, 20, undefined, true)).rejects.toThrow(
      'Failed to fetch /api/runs/admin?page=0&limit=20: 401'
    )
  })
})
