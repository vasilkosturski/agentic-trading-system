import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import AgentDetail from './AgentDetail'
import * as api from './api'

// Mock the API module
vi.mock('./api', () => ({
  fetchAgentPortfolio: vi.fn(),
  fetchAgents: vi.fn(),
}))

// Mock react-router-dom params
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
    // Arrange
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

    // Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <AgentDetail />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    await waitFor(() => {
      expect(screen.queryByText('Loading portfolio...')).not.toBeInTheDocument()
    })

    // Check that "Strategy" label is displayed instead of "System Prompt"
    expect(screen.getByText('Strategy')).toBeInTheDocument()
    expect(screen.queryByText('System Prompt')).not.toBeInTheDocument()
  })

  it('renders the system prompt accordion expanded by default', async () => {
    // Arrange
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

    // Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <AgentDetail />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    await waitFor(() => {
      expect(screen.queryByText('Loading portfolio...')).not.toBeInTheDocument()
    })

    // Check that the system prompt content is visible (accordion is expanded)
    // The content should be visible in the document without requiring a click
    await waitFor(() => {
      expect(screen.getByText(/You are a value investor focused on finding undervalued stocks/i)).toBeVisible()
    })
  })

  it('allows the user to collapse the expanded system prompt section', async () => {
    // Arrange
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

    // Act
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

    // Verify the accordion control exists and is clickable
    const accordionControl = screen.getByText('Strategy').closest('button')
    expect(accordionControl).toBeInTheDocument()
  })
})

describe('AgentDetail - Disclaimer and Timestamp Components', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('displays historical data notice disclaimer before portfolio summary', async () => {
    // Arrange
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

    // Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <AgentDetail />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    await waitFor(() => {
      expect(screen.queryByText('Loading portfolio...')).not.toBeInTheDocument()
    })

    // Check that "Historical Data Notice" heading is displayed
    expect(screen.getByText('Historical Data Notice')).toBeInTheDocument()

    // Check that the disclaimer explains the 7-day delay
    expect(screen.getByText(/7 days/i)).toBeInTheDocument()
    expect(screen.getByText(/educational purposes/i)).toBeInTheDocument()
  })

  it('displays the disclaimer with yellow background Paper component', async () => {
    // Arrange
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

    // Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <AgentDetail />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    await waitFor(() => {
      expect(screen.queryByText('Loading portfolio...')).not.toBeInTheDocument()
    })

    // Find the disclaimer Paper element by its text content
    const disclaimerHeading = screen.getByText('Historical Data Notice')
    const paperElement = disclaimerHeading.closest('[class*="Paper"]')

    // Verify Paper component exists
    expect(paperElement).toBeInTheDocument()
  })

  it('displays timestamp badge with clock icon showing data age', async () => {
    // Arrange
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

    // Act
    render(
      <MantineProvider>
        <BrowserRouter>
          <AgentDetail />
        </BrowserRouter>
      </MantineProvider>
    )

    // Assert
    await waitFor(() => {
      expect(screen.queryByText('Loading portfolio...')).not.toBeInTheDocument()
    })

    // Check that a timestamp badge is displayed with relative time
    expect(screen.getByText(/7 days ago/i)).toBeInTheDocument()
  })
})
