import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchRuns } from './api'

describe('api.ts - fetchRuns function', () => {
  beforeEach(() => {
    // Setup fetch mock
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetchRuns function signature does not include showAll parameter', () => {
    // This test ensures behavioral compliance: the function should not modify URLs based on showAll
    // We test this by examining the function's string representation
    const funcStr = fetchRuns.toString()

    // After refactoring, the function should not have 'showAll' in its parameter list
    // This will fail with current implementation which has: fetchRuns(page, limit, signal, showAll)
    const paramMatch = funcStr.match(/function\s+\w*\s*\(([^)]*)\)/)
    if (paramMatch) {
      const params = paramMatch[1]
      expect(params).not.toContain('showAll')
    }
  })

  it('calls /api/runs endpoint without showAll parameter', async () => {
    // Arrange
    const mockResponse = {
      runs: [{ runId: '123', agentId: 1, status: 'COMPLETED' }],
      total: 1,
      page: 0,
      limit: 20,
    }

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    // Act
    await fetchRuns(0, 20)

    // Assert - should call /api/runs with page and limit only, no showAll
    expect(global.fetch).toHaveBeenCalledWith('/api/runs?page=0&limit=20', undefined)
    expect(global.fetch).toHaveBeenCalledTimes(1)
  })

  it('does not append showAll query parameter to URL even when called with default parameters', async () => {
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

    // Act - call with all current parameters to test URL construction
    await fetchRuns(0, 20, undefined)

    // Assert - URL should not contain 'showAll' substring
    const callUrl = vi.mocked(global.fetch).mock.calls[0][0] as string
    expect(callUrl).not.toContain('showAll')
    // URL should be exactly this format
    expect(callUrl).toBe('/api/runs?page=0&limit=20')
  })

  it('accepts only page, limit, and signal parameters', async () => {
    // Arrange
    const mockResponse = {
      runs: [],
      total: 0,
      page: 1,
      limit: 10,
    }

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    const abortController = new AbortController()

    // Act - this should compile without showAll parameter
    await fetchRuns(1, 10, abortController.signal)

    // Assert
    expect(global.fetch).toHaveBeenCalledWith('/api/runs?page=1&limit=10', { signal: abortController.signal })
  })

  it('returns paginated runs data structure', async () => {
    // Arrange
    const mockResponse = {
      runs: [
        { runId: '1', agentId: 1, status: 'COMPLETED' },
        { runId: '2', agentId: 2, status: 'IN_PROGRESS' },
      ],
      total: 2,
      page: 0,
      limit: 20,
    }

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response)

    // Act
    const result = await fetchRuns(0, 20)

    // Assert
    expect(result).toEqual(mockResponse)
    expect(result.runs).toHaveLength(2)
    expect(result.total).toBe(2)
  })

  it('throws error when fetch fails', async () => {
    // Arrange
    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 500,
    } as Response)

    // Act & Assert
    await expect(fetchRuns(0, 20)).rejects.toThrow('Failed to fetch /api/runs?page=0&limit=20: 500')
  })

  it('always calls public endpoint regardless of any legacy parameters', async () => {
    // This test ensures the function signature no longer accepts showAll
    // and always uses /api/runs endpoint

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

    // Act - call fetchRuns with the three allowed parameters
    await fetchRuns(5, 50, undefined)

    // Assert - should always call /api/runs without showAll parameter
    const callUrl = vi.mocked(global.fetch).mock.calls[0][0] as string
    expect(callUrl).toBe('/api/runs?page=5&limit=50')
    expect(callUrl).not.toContain('showAll')

    // Verify the function accepts exactly 3 parameters (page, limit, signal)
    // This will be validated by TypeScript compilation
    const signal = new AbortController().signal
    await fetchRuns(0, 20, signal)
    expect(vi.mocked(global.fetch)).toHaveBeenCalledWith('/api/runs?page=0&limit=20', { signal })
  })
})
