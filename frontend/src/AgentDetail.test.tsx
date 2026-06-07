import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import AgentDetail from './AgentDetail'
import * as api from './api'
import { makeMockPortfolio, makeMockAgent } from './test/factories'

vi.mock('./api', () => ({
  fetchAgentPortfolio: vi.fn(),
  fetchAgents: vi.fn(),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useParams: () => ({ id: '1' }),
    useNavigate: () => vi.fn(),
  }
})

function renderAgentDetail() {
  return render(
    <MantineProvider>
      <BrowserRouter>
        <AgentDetail />
      </BrowserRouter>
    </MantineProvider>,
  )
}

describe('AgentDetail - System Prompt Section', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('displays the system prompt section with user-friendly label "Strategy"', async () => {
    vi.mocked(api.fetchAgentPortfolio).mockResolvedValue(makeMockPortfolio({ agentName: 'Warren' }))
    vi.mocked(api.fetchAgents).mockResolvedValue([
      makeMockAgent({ id: 1, name: 'Warren', systemPrompt: 'You are a value investor.' }),
    ])

    renderAgentDetail()

    await waitFor(() => {
      expect(screen.queryByText('Loading portfolio...')).not.toBeInTheDocument()
    })

    expect(screen.getByText('Strategy')).toBeInTheDocument()
    expect(screen.queryByText('System Prompt')).not.toBeInTheDocument()
  })

  it('renders the system prompt accordion expanded by default', async () => {
    const prompt = 'You are a value investor focused on finding undervalued stocks.'
    vi.mocked(api.fetchAgentPortfolio).mockResolvedValue(makeMockPortfolio({ agentName: 'Warren' }))
    vi.mocked(api.fetchAgents).mockResolvedValue([
      makeMockAgent({ id: 1, name: 'Warren', systemPrompt: prompt }),
    ])

    renderAgentDetail()

    await waitFor(() => {
      expect(screen.queryByText('Loading portfolio...')).not.toBeInTheDocument()
    })

    await waitFor(() => {
      expect(screen.getByText(/You are a value investor focused on finding undervalued stocks/i)).toBeVisible()
    })
  })
})

describe('AgentDetail - Promise.all partial-failure resilience', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('still renders the portfolio with fallback agent name when fetchAgents rejects', async () => {
    vi.mocked(api.fetchAgentPortfolio).mockResolvedValue(
      makeMockPortfolio({
        agentName: 'Warren Backend',
        holdingsCount: 0,
        transactionCount: 0,
      }),
    )
    vi.mocked(api.fetchAgents).mockRejectedValue(new Error('agents endpoint down'))

    renderAgentDetail()

    await waitFor(() => {
      expect(screen.queryByText('Loading portfolio...')).not.toBeInTheDocument()
    })

    expect(screen.getByText('Warren Backend')).toBeInTheDocument()
    expect(screen.queryByText(/agents endpoint down/i)).toBeNull()
  })
})

describe('AgentDetail - Disclaimer and Timestamp Components', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('displays historical data notice disclaimer before portfolio summary', async () => {
    vi.mocked(api.fetchAgentPortfolio).mockResolvedValue(makeMockPortfolio({ agentName: 'Warren' }))
    vi.mocked(api.fetchAgents).mockResolvedValue([makeMockAgent({ id: 1, name: 'Warren' })])

    renderAgentDetail()

    await waitFor(() => {
      expect(screen.queryByText('Loading portfolio...')).not.toBeInTheDocument()
    })

    expect(screen.getByText('Historical Data Notice')).toBeInTheDocument()
    expect(screen.getByText(/7 days/i)).toBeInTheDocument()
    expect(screen.getByText(/educational purposes/i)).toBeInTheDocument()
  })

  it('displays timestamp badge with clock icon showing data age', async () => {
    const sevenDaysAgo = new Date()
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)

    vi.mocked(api.fetchAgentPortfolio).mockResolvedValue(
      makeMockPortfolio({
        agentName: 'Warren',
        lastUpdated: sevenDaysAgo.toISOString(),
      }),
    )
    vi.mocked(api.fetchAgents).mockResolvedValue([makeMockAgent({ id: 1, name: 'Warren' })])

    renderAgentDetail()

    await waitFor(() => {
      expect(screen.queryByText('Loading portfolio...')).not.toBeInTheDocument()
    })

    expect(screen.getByText(/7 days ago/i)).toBeInTheDocument()
  })
})
