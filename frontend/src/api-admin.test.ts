import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchRuns } from './api'
import * as auth from './auth'

// Mock auth module
vi.mock('./auth')

describe('api.ts - fetchRuns with showAll parameter for admin endpoint', () => {
  beforeEach(() => {
    // Setup fetch mock
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('calls /api/runs endpoint when showAll is false', async () => {
    // Arrange
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

    // Act
    await fetchRuns(0, 20, undefined, false)

    // Assert - should call public endpoint (with empty options object, no auth)
    expect(global.fetch).toHaveBeenCalledWith('/api/runs?page=0&limit=20', {})
    expect(global.fetch).toHaveBeenCalledTimes(1)
  })

  it('calls /api/runs endpoint when showAll is not provided (defaults to false)', async () => {
    // Arrange
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

    // Act - call without showAll parameter
    await fetchRuns(0, 20)

    // Assert - should call public endpoint by default
    const callUrl = vi.mocked(global.fetch).mock.calls[0][0] as string
    expect(callUrl).toBe('/api/runs?page=0&limit=20')
  })

  it('calls /api/runs/admin endpoint when showAll is true', async () => {
    // Arrange
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

    // Act
    await fetchRuns(0, 20, undefined, true)

    // Assert - should call admin endpoint with auth header
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

  it('does not append showAll as query parameter - endpoint path changes instead', async () => {
    // Arrange
    const mockResponse = {
      runs: [],
      total: 188,
      page: 0,
      limit: 20,
    }

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    // Act - call with showAll=true
    await fetchRuns(0, 20, undefined, true)

    // Assert - URL should change path, not add showAll query param
    const callUrl = vi.mocked(global.fetch).mock.calls[0][0] as string
    expect(callUrl).toBe('/api/runs/admin?page=0&limit=20')
    expect(callUrl).not.toContain('showAll=')
  })

  it('accepts showAll with AbortSignal', async () => {
    // Arrange
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

    // Act - pass signal and showAll
    await fetchRuns(1, 10, abortController.signal, true)

    // Assert - should include both signal and auth header
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
    // Arrange
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

    // Act
    const result = await fetchRuns(0, 20, undefined, true)

    // Assert
    expect(result).toEqual(mockResponse)
    expect(result.runs).toHaveLength(2)
    expect(result.total).toBe(188)
  })

  it('throws error when admin endpoint fetch fails', async () => {
    // Arrange
    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 401, // Unauthorized
    } as Response)

    // Act & Assert
    await expect(fetchRuns(0, 20, undefined, true)).rejects.toThrow(
      'Failed to fetch /api/runs/admin?page=0&limit=20: 401'
    )
  })
})
