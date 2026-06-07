import type { AgentPortfolio, Agent, RunDetailResponse, TradingRun } from '../types.ts'

const BASE_RUN: TradingRun = {
  runId: 42,
  agentId: 7,
  status: 'COMPLETED',
  phase: 'COMPLETED',
  decision: 'BUY',
  symbol: 'AAPL',
  startedAt: '2025-01-01T00:00:00Z',
  completedAt: '2025-01-01T01:00:00Z',
}

const BASE_PORTFOLIO: AgentPortfolio = {
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

const BASE_AGENT: Agent = {
  id: 1,
  name: 'Warren',
  style: 'Value Investing',
  systemPrompt: 'You are a value investor.',
}

const BASE_RUN_DETAIL: RunDetailResponse = {
  run: BASE_RUN,
  research: null,
  decision: null,
  execution: null,
}

export function makeMockPortfolio(overrides: Partial<AgentPortfolio> = {}): AgentPortfolio {
  return { ...BASE_PORTFOLIO, ...overrides }
}

export function makeMockAgent(overrides: Partial<Agent> = {}): Agent {
  return { ...BASE_AGENT, ...overrides }
}

export function makeMockRunDetail(overrides: Partial<RunDetailResponse> = {}): RunDetailResponse {
  return {
    ...BASE_RUN_DETAIL,
    ...overrides,
    run: { ...BASE_RUN_DETAIL.run, ...(overrides.run ?? {}) },
  }
}
