import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import RunsTable from './App'
import * as api from './api'

// Mock the API module
vi.mock('./api', () => ({
  fetchRuns: vi.fn(),
  fetchAgents: vi.fn(),
  fetchSnapshots: vi.fn(),
}))

describe('App.tsx - showAll parameter removal', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Setup default mock responses
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
      total: 1,
      page: 0,
      limit: 20,
    })

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

  it('calls fetchRuns without showAll parameter on initial load', async () => {
    // Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <RunsTable />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    await waitFor(() => {
      expect(api.fetchRuns).toHaveBeenCalled()
    })

    // Check that fetchRuns was called with exactly 3 parameters (page, limit, signal)
    // After refactoring, there should be NO 4th parameter (showAll)
    const firstCall = vi.mocked(api.fetchRuns).mock.calls[0]
    expect(firstCall[0]).toBe(0) // page
    expect(firstCall[1]).toBe(20) // limit
    expect(firstCall[2]).toBeDefined() // AbortSignal

    // This is the key test: should be exactly 3 parameters, not 4
    // Current code passes showAll as 4th parameter, after refactoring it won't
    expect(firstCall).toHaveLength(3)
  })

  it('renders runs table successfully without showAll functionality', async () => {
    // Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <RunsTable />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert - component loads and displays data
    await waitFor(() => {
      expect(screen.queryByText('Loading runs...')).not.toBeInTheDocument()
    })

    expect(screen.getByText('Trading Dashboard')).toBeInTheDocument()
    expect(api.fetchRuns).toHaveBeenCalledTimes(1)
  })

  it('does not have showAll in useEffect dependency array', async () => {
    // This test verifies behavior: component should not re-fetch when URL changes with ?showAll
    // We test this by verifying fetchRuns is only called once on mount, not on URL parameter changes

    // Act
    const { rerender } = render(
      <MantineProvider>
        <BrowserRouter>
          <RunsTable />
        </BrowserRouter>
      </MantineProvider>
    )

    await waitFor(() => {
      expect(api.fetchRuns).toHaveBeenCalledTimes(1)
    })

    // Clear the mock to track new calls
    vi.clearAllMocks()
    vi.mocked(api.fetchRuns).mockResolvedValue({
      runs: [],
      total: 0,
      page: 0,
      limit: 20,
    })

    // Rerender (simulating URL change, but showAll is not in dependencies so shouldn't trigger)
    rerender(
      <MantineProvider>
        <BrowserRouter>
          <RunsTable />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert - fetchRuns should not be called again because showAll is not in dependencies
    await waitFor(() => {
      // No new calls expected
      expect(api.fetchRuns).toHaveBeenCalledTimes(0)
    })
  })

  it('displays runs from the 7-day filtered endpoint', async () => {
    // Arrange
    const mockRuns = [
      {
        runId: 'run-123',
        agentId: 1,
        status: 'COMPLETED',
        decision: 'HOLD',
        symbol: 'TSLA',
        startedAt: '2025-01-02T10:00:00Z',
        completedAt: '2025-01-02T11:00:00Z',
      },
      {
        runId: 'run-456',
        agentId: 1,
        status: 'IN_PROGRESS',
        decision: null,
        symbol: 'GOOGL',
        startedAt: '2025-01-03T10:00:00Z',
        completedAt: null,
      },
    ]

    vi.mocked(api.fetchRuns).mockResolvedValue({
      runs: mockRuns,
      total: 2,
      page: 0,
      limit: 20,
    })

    // Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <RunsTable />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    await waitFor(() => {
      expect(screen.getByText('run-123')).toBeInTheDocument()
      expect(screen.getByText('run-456')).toBeInTheDocument()
    })

    expect(screen.getByText('TSLA')).toBeInTheDocument()
    expect(screen.getByText('GOOGL')).toBeInTheDocument()
  })

  it('does not extract showAll from URL searchParams', async () => {
    // This test checks that the component doesn't read showAll from URL
    // Current code has: const showAll = searchParams.get('showAll') === 'true'
    // After refactoring, this line should not exist

    // We'll test this by checking the component's behavior
    // The component should work the same regardless of URL parameters

    // Act - render with ?showAll=true in URL
    render(
      <MantineProvider>
        <BrowserRouter initialEntries={['/?showAll=true']}>
          <RunsTable />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert - should still call fetchRuns with only 3 parameters
    await waitFor(() => {
      expect(api.fetchRuns).toHaveBeenCalled()
    })

    const callArgs = vi.mocked(api.fetchRuns).mock.calls[0]
    // Should NOT pass showAll as 4th parameter
    expect(callArgs).toHaveLength(3)
  })
})
