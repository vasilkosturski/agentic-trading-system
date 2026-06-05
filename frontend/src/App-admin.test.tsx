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

describe('App.tsx - showAll parameter for admin endpoint', () => {
  beforeEach(() => {
    vi.clearAllMocks()

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

    render(
      <MantineProvider>
        <MemoryRouter initialEntries={['/']}>
          <RunsTable />
        </MemoryRouter>
      </MantineProvider>
    )

    await waitFor(() => {
      expect(api.fetchRuns).toHaveBeenCalled()
    })

    const firstCall = vi.mocked(api.fetchRuns).mock.calls[0]
    expect(firstCall[0]).toBe(0)
    expect(firstCall[1]).toBe(20)
    expect(firstCall[2]).toBeDefined()
    expect(firstCall[3]).toBe(false)
  })

  it('calls fetchRuns with showAll=true when URL has ?showAll=true', async () => {
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

    render(
      <MantineProvider>
        <MemoryRouter initialEntries={['/?showAll=true']}>
          <RunsTable />
        </MemoryRouter>
      </MantineProvider>
    )

    await waitFor(() => {
      expect(api.fetchRuns).toHaveBeenCalled()
    })

    const firstCall = vi.mocked(api.fetchRuns).mock.calls[0]
    expect(firstCall[0]).toBe(0)
    expect(firstCall[1]).toBe(20)
    expect(firstCall[2]).toBeDefined()
    expect(firstCall[3]).toBe(true)
  })

  it('reads showAll from URL searchParams correctly', async () => {
    vi.mocked(api.fetchRuns).mockResolvedValue({
      runs: [],
      total: 0,
      page: 0,
      limit: 20,
    })

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
      total: 188,
      page: 0,
      limit: 20,
    })

    render(
      <MantineProvider>
        <MemoryRouter initialEntries={['/?showAll=true']}>
          <RunsTable />
        </MemoryRouter>
      </MantineProvider>
    )

    await waitFor(() => {
      expect(api.fetchRuns).toHaveBeenCalledWith(0, 20, expect.any(Object), true)
    })

    await waitFor(() => {
      expect(screen.getByText('admin-run-1')).toBeInTheDocument()
    })
  })
})
