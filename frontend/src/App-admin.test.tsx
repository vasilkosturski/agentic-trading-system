import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import RunsTable from './App'
import * as api from './api'

// Mock the API module
vi.mock('./api', () => ({
  fetchRuns: vi.fn(),
  fetchAgents: vi.fn(),
  fetchSnapshots: vi.fn(),
}))

describe('App.tsx - showAll parameter for admin endpoint', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Setup default mock responses
    vi.mocked(api.fetchAgents).mockResolvedValue([
      {
        id: 1,
        name: 'Test Agent',
        style: 'Value',
        systemPrompt: 'Test prompt',
      },
    ])

    vi.mocked(api.fetchSnapshots).mockResolvedValue([])
  })

  it('calls fetchRuns with showAll=false when URL has no showAll parameter', async () => {
    // Arrange
    vi.mocked(api.fetchRuns).mockResolvedValue({
      runs: [
        {
          runId: '1',
          agentId: 1,
          status: 'COMPLETED',
          decision: 'BUY',
          symbol: 'AAPL',
          startedAt: '2025-01-01T00:00:00Z',
          completedAt: '2025-01-01T01:00:00Z',
        },
      ],
      total: 104,
      page: 0,
      limit: 20,
    })

    // Act - render without showAll in URL
    render(
      <MantineProvider>
        <MemoryRouter initialEntries={['/']}>
          <RunsTable />
        </MemoryRouter>
      </MantineProvider>
    )

    // Assert
    await waitFor(() => {
      expect(api.fetchRuns).toHaveBeenCalled()
    })

    const firstCall = vi.mocked(api.fetchRuns).mock.calls[0]
    expect(firstCall[0]).toBe(0) // page
    expect(firstCall[1]).toBe(20) // limit
    expect(firstCall[2]).toBeDefined() // AbortSignal
    expect(firstCall[3]).toBe(false) // showAll should be false
  })

  it('calls fetchRuns with showAll=true when URL has ?showAll=true', async () => {
    // Arrange
    vi.mocked(api.fetchRuns).mockResolvedValue({
      runs: [
        {
          runId: '1',
          agentId: 1,
          status: 'COMPLETED',
          decision: 'BUY',
          symbol: 'AAPL',
          startedAt: '2025-01-01T00:00:00Z',
          completedAt: '2025-01-01T01:00:00Z',
        },
      ],
      total: 188,
      page: 0,
      limit: 20,
    })

    // Act - render with ?showAll=true in URL
    render(
      <MantineProvider>
        <MemoryRouter initialEntries={['/?showAll=true']}>
          <RunsTable />
        </MemoryRouter>
      </MantineProvider>
    )

    // Assert
    await waitFor(() => {
      expect(api.fetchRuns).toHaveBeenCalled()
    })

    const firstCall = vi.mocked(api.fetchRuns).mock.calls[0]
    expect(firstCall[0]).toBe(0) // page
    expect(firstCall[1]).toBe(20) // limit
    expect(firstCall[2]).toBeDefined() // AbortSignal
    expect(firstCall[3]).toBe(true) // showAll should be true
  })

  it('reads showAll from URL searchParams correctly', async () => {
    // Arrange - test various URL parameter values
    vi.mocked(api.fetchRuns).mockResolvedValue({
      runs: [],
      total: 0,
      page: 0,
      limit: 20,
    })

    // Act & Assert - ?showAll=false should be false
    const { unmount } = render(
      <MantineProvider>
        <MemoryRouter initialEntries={['/?showAll=false']}>
          <RunsTable />
        </MemoryRouter>
      </MantineProvider>
    )

    await waitFor(() => {
      expect(api.fetchRuns).toHaveBeenCalled()
    })

    expect(vi.mocked(api.fetchRuns).mock.calls[0][3]).toBe(false)
    unmount()
    vi.clearAllMocks()

    // Act & Assert - ?showAll=anything-else should be false
    render(
      <MantineProvider>
        <MemoryRouter initialEntries={['/?showAll=yes']}>
          <RunsTable />
        </MemoryRouter>
      </MantineProvider>
    )

    await waitFor(() => {
      expect(api.fetchRuns).toHaveBeenCalled()
    })

    expect(vi.mocked(api.fetchRuns).mock.calls[0][3]).toBe(false)
  })

  it('displays runs when showAll=true and calls admin endpoint', async () => {
    // Arrange
    vi.mocked(api.fetchRuns).mockResolvedValue({
      runs: [
        {
          runId: 'admin-run-1',
          agentId: 1,
          status: 'COMPLETED',
          decision: 'HOLD',
          symbol: 'TSLA',
          startedAt: '2025-01-02T10:00:00Z',
          completedAt: '2025-01-02T11:00:00Z',
        },
      ],
      total: 188, // Admin endpoint returns all runs
      page: 0,
      limit: 20,
    })

    // Act
    render(
      <MantineProvider>
        <MemoryRouter initialEntries={['/?showAll=true']}>
          <RunsTable />
        </MemoryRouter>
      </MantineProvider>
    )

    // Assert - should call fetchRuns with showAll=true
    await waitFor(() => {
      expect(api.fetchRuns).toHaveBeenCalledWith(0, 20, expect.any(Object), true)
    })

    // Should display the run data
    await waitFor(() => {
      expect(screen.getByText('admin-run-1')).toBeInTheDocument()
    })
  })
})
