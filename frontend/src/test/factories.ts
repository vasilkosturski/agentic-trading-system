import type {
  Agent,
  AgentPortfolio,
  DecisionPhase,
  ResearchPhase,
  RunDetailResponse,
  TradingRun,
} from '@/lib/types.ts'

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

const BASE_RESEARCH_PHASE: ResearchPhase = {
  researchId: 100,
  candidates: ['JPM', 'BAC'],
  sources: [],
  researchNotes: 'Mock research notes',
  toolCalls: [],
  latencyMs: 1500,
  metrics: null,
  systemPrompt: null,
  taskPrompt: null,
  guardrailAttempts: 1,
  guardrailIssues: null,
  guardrailOutcome: 'first_try',
  guardrailFailedOutput: null,
}

const BASE_DECISION_PHASE: DecisionPhase = {
  decisionId: 200,
  decision: 'BUY',
  symbol: 'JPM',
  quantity: 10,
  reasoning: {
    rationale: 'mock rationale',
    portfolioContext: 'mock portfolio context',
    historicalContext: 'mock historical context',
    researchContext: 'mock research context',
  },
  sources: [],
  toolCalls: [],
  latencyMs: 2500,
  metrics: null,
  systemPrompt: null,
  taskPrompt: null,
  guardrailAttempts: 1,
  guardrailIssues: null,
  guardrailOutcome: 'first_try',
  guardrailFailedOutput: null,
}

export function makeMockResearchPhase(overrides: Partial<ResearchPhase> = {}): ResearchPhase {
  return { ...BASE_RESEARCH_PHASE, ...overrides }
}

export function makeMockDecisionPhase(overrides: Partial<DecisionPhase> = {}): DecisionPhase {
  return { ...BASE_DECISION_PHASE, ...overrides }
}
