import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useState } from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, useSearchParams } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import RunsTable from './App'
import * as api from './api'

vi.mock('./api', () => ({
  fetchRuns: vi.fn(),
  fetchAgents: vi.fn(),
  fetchSnapshots: vi.fn(),
}))

function Toggler() {
  // Trivial child that flips the showAll query param in-place so we exercise
  // the same useEffect dep change that the showAll route flag does in
  // production, without needing to re-mount the whole tree.
  const [params, setParams] = useSearchParams()
  const [n, setN] = useState(0)
  return (
    <>
      <button
        onClick={() => {
          params.set('showAll', n === 0 ? 'true' : 'false')
          setParams(params)
          setN(n + 1)
        }}
      >
        toggle
      </button>
      <RunsTable />
    </>
  )
}

describe('App.tsx — pagination state resets on showAll toggle (R5)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.fetchAgents).mockResolvedValue([])
    vi.mocked(api.fetchSnapshots).mockResolvedValue([])
    vi.mocked(api.fetchRuns).mockResolvedValue({
      runs: [
        {
          runId: 1,
          agentId: 1,
          status: 'COMPLETED',
          phase: 'COMPLETED',
          decision: 'BUY',
          symbol: 'AAPL',
          startedAt: '2025-01-01T00:00:00Z',
          completedAt: '2025-01-01T01:00:00Z',
        },
      ],
      total: 50,
      page: 0,
      limit: 20,
    })
  })

  it('refetches page 0 of the new endpoint when showAll flips', async () => {
    render(
      <MantineProvider>
        <MemoryRouter initialEntries={['/']}>
          <Toggler />
        </MemoryRouter>
      </MantineProvider>,
    )

    await waitFor(() => {
      expect(api.fetchRuns).toHaveBeenCalled()
    })

    // First call: public endpoint, page 0.
    expect(vi.mocked(api.fetchRuns).mock.calls[0][0]).toBe(0)
    expect(vi.mocked(api.fetchRuns).mock.calls[0][3]).toBe(false)

    vi.mocked(api.fetchRuns).mockClear()
    fireEvent.click(screen.getByText('toggle'))

    await waitFor(() => {
      expect(api.fetchRuns).toHaveBeenCalled()
    })

    // After the toggle, the initial-load effect must refetch page 0 of the
    // admin endpoint — not pageRef.current + 1.
    expect(vi.mocked(api.fetchRuns).mock.calls[0][0]).toBe(0)
    expect(vi.mocked(api.fetchRuns).mock.calls[0][3]).toBe(true)
  })
})
