import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import RunDetail from './RunDetail'
import * as api from './api'

vi.mock('./api', () => ({
  fetchRunDetail: vi.fn(),
  fetchAgents: vi.fn(),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useParams: () => ({ id: '42' }),
    useNavigate: () => vi.fn(),
  }
})

describe('RunDetail.tsx — Promise.all partial-failure resilience (R1)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('still renders run detail with fallback agent name when fetchAgents rejects', async () => {
    vi.mocked(api.fetchRunDetail).mockResolvedValue({
      run: {
        runId: 42,
        agentId: 7,
        status: 'COMPLETED',
        phase: 'COMPLETED',
        decision: 'BUY',
        symbol: 'AAPL',
        startedAt: '2025-01-01T00:00:00Z',
        completedAt: '2025-01-01T01:00:00Z',
      },
      research: null,
      decision: null,
      execution: null,
    })
    vi.mocked(api.fetchAgents).mockRejectedValue(new Error('agents endpoint down'))

    render(
      <MantineProvider>
        <MemoryRouter initialEntries={['/runs/42']}>
          <RunDetail />
        </MemoryRouter>
      </MantineProvider>
    )

    await waitFor(() => {
      expect(screen.queryByText(/Loading run details/i)).toBeNull()
    })

    expect(screen.getByText(/Agent #7/)).toBeInTheDocument()

    expect(screen.queryByText(/agents endpoint down/i)).toBeNull()
  })
})
