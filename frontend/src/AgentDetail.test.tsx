import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import AgentDetail from './AgentDetail'
import * as api from './api'

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

describe('AgentDetail - System Prompt Section', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('displays the system prompt section with user-friendly label "Strategy"', async () => {
    const mockPortfolio = {
      agentName: 'Warren',
      balance: 10000,
      holdingsValue: 5000,
      totalPortfolioValue: 15000,
      initialBalance: 10000,
      totalProfitLoss: 500,
      profitLossPercent: 3.45,
      lastUpdated: '2025-01-01T00:00:00Z',
      holdingsCount: 3,
      transactionCount: 5,
      holdings: [],
    }

    const mockAgents = [
      {
        id: 1,
        name: 'Warren',
        style: 'Value Investing',
        systemPrompt: 'You are a value investor.',
      },
    ]

    vi.mocked(api.fetchAgentPortfolio).mockResolvedValue(mockPortfolio)
    vi.mocked(api.fetchAgents).mockResolvedValue(mockAgents)

    render(
      <MantineProvider>
        <BrowserRouter>
          <AgentDetail />
        </BrowserRouter>
      </MantineProvider>
    )

    await waitFor(() => {
      expect(screen.queryByText('Loading portfolio...')).not.toBeInTheDocument()
    })

    expect(screen.getByText('Strategy')).toBeInTheDocument()
    expect(screen.queryByText('System Prompt')).not.toBeInTheDocument()
  })

  it('renders the system prompt accordion expanded by default', async () => {
    const mockPortfolio = {
      agentName: 'Warren',
      balance: 10000,
      holdingsValue: 5000,
      totalPortfolioValue: 15000,
      initialBalance: 10000,
      totalProfitLoss: 500,
      profitLossPercent: 3.45,
      lastUpdated: '2025-01-01T00:00:00Z',
      holdingsCount: 3,
      transactionCount: 5,
      holdings: [],
    }

    const mockAgents = [
      {
        id: 1,
        name: 'Warren',
        style: 'Value Investing',
        systemPrompt: 'You are a value investor focused on finding undervalued stocks.',
      },
    ]

    vi.mocked(api.fetchAgentPortfolio).mockResolvedValue(mockPortfolio)
    vi.mocked(api.fetchAgents).mockResolvedValue(mockAgents)

    render(
      <MantineProvider>
        <BrowserRouter>
          <AgentDetail />
        </BrowserRouter>
      </MantineProvider>
    )

    await waitFor(() => {
      expect(screen.queryByText('Loading portfolio...')).not.toBeInTheDocument()
    })

    await waitFor(() => {
      expect(screen.getByText(/You are a value investor focused on finding undervalued stocks/i)).toBeVisible()
    })
  })

})

describe('AgentDetail - Promise.all partial-failure resilience (R1)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('still renders the portfolio with fallback agent name when fetchAgents rejects', async () => {
    const mockPortfolio = {
      agentName: 'Warren Backend',
      balance: 10000,
      holdingsValue: 5000,
      totalPortfolioValue: 15000,
      initialBalance: 10000,
      totalProfitLoss: 500,
      profitLossPercent: 3.45,
      lastUpdated: '2025-01-01T00:00:00Z',
      holdingsCount: 0,
      transactionCount: 0,
      holdings: [],
    }

    vi.mocked(api.fetchAgentPortfolio).mockResolvedValue(mockPortfolio)
    vi.mocked(api.fetchAgents).mockRejectedValue(new Error('agents endpoint down'))

    render(
      <MantineProvider>
        <BrowserRouter>
          <AgentDetail />
        </BrowserRouter>
      </MantineProvider>
    )

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
    const mockPortfolio = {
      agentName: 'Warren',
      balance: 10000,
      holdingsValue: 5000,
      totalPortfolioValue: 15000,
      initialBalance: 10000,
      totalProfitLoss: 500,
      profitLossPercent: 3.45,
      lastUpdated: '2025-01-01T00:00:00Z',
      holdingsCount: 3,
      transactionCount: 5,
      holdings: [],
    }

    const mockAgents = [
      {
        id: 1,
        name: 'Warren',
        style: 'Value Investing',
        systemPrompt: 'You are a value investor.',
      },
    ]

    vi.mocked(api.fetchAgentPortfolio).mockResolvedValue(mockPortfolio)
    vi.mocked(api.fetchAgents).mockResolvedValue(mockAgents)

    render(
      <MantineProvider>
        <BrowserRouter>
          <AgentDetail />
        </BrowserRouter>
      </MantineProvider>
    )

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

    const mockPortfolio = {
      agentName: 'Warren',
      balance: 10000,
      holdingsValue: 5000,
      totalPortfolioValue: 15000,
      initialBalance: 10000,
      totalProfitLoss: 500,
      profitLossPercent: 3.45,
      lastUpdated: sevenDaysAgo.toISOString(),
      holdingsCount: 3,
      transactionCount: 5,
      holdings: [],
    }

    const mockAgents = [
      {
        id: 1,
        name: 'Warren',
        style: 'Value Investing',
        systemPrompt: 'You are a value investor.',
      },
    ]

    vi.mocked(api.fetchAgentPortfolio).mockResolvedValue(mockPortfolio)
    vi.mocked(api.fetchAgents).mockResolvedValue(mockAgents)

    render(
      <MantineProvider>
        <BrowserRouter>
          <AgentDetail />
        </BrowserRouter>
      </MantineProvider>
    )

    await waitFor(() => {
      expect(screen.queryByText('Loading portfolio...')).not.toBeInTheDocument()
    })

    expect(screen.getByText(/7 days ago/i)).toBeInTheDocument()
  })
})
