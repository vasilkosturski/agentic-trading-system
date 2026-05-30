import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import RunsTable from './App'
import * as api from './api'

vi.mock('./api', () => ({
  fetchRuns: vi.fn(),
  fetchAgents: vi.fn(),
  fetchSnapshots: vi.fn(),
}))

describe('App.tsx — Promise.all partial-failure resilience (R1)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('still renders the runs table when fetchAgents rejects (cosmetic fetch must not block primary content)', async () => {
    // Arrange — primary fetch succeeds, cosmetic fetch (agents) fails.
    vi.mocked(api.fetchRuns).mockResolvedValue({
      runs: [
        {
          runId: 42,
          agentId: 7,
          status: 'COMPLETED',
          phase: 'COMPLETED',
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
    vi.mocked(api.fetchAgents).mockRejectedValue(new Error('agents endpoint down'))
    vi.mocked(api.fetchSnapshots).mockResolvedValue([])

    // Act
    render(
      <MantineProvider>
        <MemoryRouter initialEntries={['/']}>
          <RunsTable />
        </MemoryRouter>
      </MantineProvider>
    )

    // Assert — the runs table must render even though fetchAgents rejected.
    await waitFor(() => {
      expect(screen.getByText('42')).toBeInTheDocument()
    })

    // Fallback agent name "Agent #7" should appear since the agents map is empty.
    expect(screen.getByText('Agent #7')).toBeInTheDocument()

    // No error message should be painted from the rejected cosmetic fetch.
    expect(screen.queryByText(/agents endpoint down/i)).toBeNull()
  })
})
