import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import RunsTable from './App'
import * as api from '@/lib/api'

vi.mock('@/lib/api', () => ({
  fetchRuns: vi.fn(),
  fetchAgents: vi.fn(),
  fetchSnapshots: vi.fn(),
}))

describe('App.tsx — Promise.all partial-failure resilience', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.fetchSnapshots).mockResolvedValue([])
  })

  it('still renders the runs table when fetchAgents rejects (cosmetic fetch must not block primary content)', async () => {
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

    render(
      <MantineProvider>
        <MemoryRouter initialEntries={['/']}>
          <RunsTable />
        </MemoryRouter>
      </MantineProvider>,
    )

    await waitFor(() => {
      expect(screen.getByText('42')).toBeInTheDocument()
    })

    expect(screen.getByText('Agent #7')).toBeInTheDocument()
    expect(screen.queryByText(/agents endpoint down/i)).toBeNull()
  })
})

describe('App.tsx — showAll parameter for admin endpoint', () => {
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

  describe.each([
    { url: '/', expected: false, label: 'no showAll parameter' },
    { url: '/?showAll=true', expected: true, label: '?showAll=true' },
    { url: '/?showAll=false', expected: false, label: '?showAll=false' },
    { url: '/?showAll=yes', expected: false, label: '?showAll=yes' },
  ])('showAll URL variant: $label', ({ url, expected }) => {
    it(`calls fetchRuns with showAll=${expected}`, async () => {
      vi.mocked(api.fetchRuns).mockResolvedValue({
        runs: [],
        total: 0,
        page: 0,
        limit: 20,
      })

      render(
        <MantineProvider>
          <MemoryRouter initialEntries={[url]}>
            <RunsTable />
          </MemoryRouter>
        </MantineProvider>,
      )

      await waitFor(() => expect(api.fetchRuns).toHaveBeenCalled())
      expect(vi.mocked(api.fetchRuns).mock.calls[0][3]).toBe(expected)
    })
  })

  it('displays runs from the admin endpoint when showAll=true', async () => {
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
      </MantineProvider>,
    )

    await waitFor(() => {
      expect(api.fetchRuns).toHaveBeenCalledWith(0, 20, expect.any(Object), true)
    })

    await waitFor(() => {
      expect(screen.getByText('admin-run-1')).toBeInTheDocument()
    })
  })
})
