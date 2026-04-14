export type RunStatus = 'COMPLETED' | 'IN_PROGRESS' | 'FAILED'
export type RunPhase =
  | 'INITIALIZING'
  | 'RESEARCHING'
  | 'DECIDING'
  | 'TRADING'
  | 'COMPLETED'
  | 'FAILED'
export type TradeDecision = 'BUY' | 'SELL' | 'HOLD'

export interface TradingRun {
  runId: number
  agentId: number
  status: RunStatus
  phase: RunPhase
  decision: TradeDecision | null
  symbol: string | null
  startedAt: string
  completedAt: string | null
  errorMessage?: string | null
}

export interface Agent {
  id: number
  name: string
  style?: string
  systemPrompt?: string
}

export interface Source {
  type: string
  title: string | null
  url: string | null
  description: string | null
}

export interface ToolCall {
  tool: string
  params: Record<string, unknown>
  error: boolean | null
  errorMessage: string | null
}

export interface Reasoning {
  researchContext: string
  portfolioContext: string
  historicalContext: string
}

export interface UsageMetrics {
  tokensUsed: number | null
  inputTokens: number | null
  outputTokens: number | null
  numTurns: number | null
  cachedTokens: number | null
  reasoningTokens: number | null
  costUsd: number | null
  modelName: string | null
}

export interface ResearchPhase {
  researchId: number
  candidates: string[]
  sources: Source[]
  researchNotes: string
  toolCalls: ToolCall[]
  latencyMs: number
  metrics: UsageMetrics | null
  systemPrompt: string | null
  taskPrompt: string | null
}

export interface DecisionPhase {
  decisionId: number
  decision: TradeDecision
  symbol: string
  quantity: number
  reasoning: Reasoning
  sources: Source[]
  toolCalls: ToolCall[]
  latencyMs: number
  metrics: UsageMetrics | null
  systemPrompt: string | null
  taskPrompt: string | null
}

export interface TradeDetail {
  symbol: string
  transactionType: string
  quantity: number
  price: number
  totalAmount: number
}

export interface ExecutionPhase {
  executionId: number
  tradeId: number | null
  status: string
  errorDetails: string | null
  trade: TradeDetail | null
}

export interface RunDetailResponse {
  run: TradingRun
  research: ResearchPhase | null
  decision: DecisionPhase | null
  execution: ExecutionPhase | null
}

export interface Holding {
  symbol: string
  quantity: number
  averagePrice: number
  currentPrice: number | null
  marketValue: number | null
  costBasis: number | null
  unrealizedPnl: number | null
  gainLossPercent: number | null
  cached: boolean | null
  priceTimestamp: string | null
}

export interface AgentPortfolio {
  agentName: string
  balance: number
  holdingsValue: number
  totalPortfolioValue: number
  initialBalance: number
  totalProfitLoss: number
  profitLossPercent: number
  lastUpdated: string | null
  holdingsCount: number
  transactionCount: number
  holdings: Holding[]
}

export interface PortfolioSnapshot {
  agentName: string
  timestamp: string
  totalValue: number
  cashBalance: number | null
  holdingsValue: number | null
  totalPnl: number | null
  totalReturnPercent: number | null
}
