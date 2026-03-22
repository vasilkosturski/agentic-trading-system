export type RunStatus = 'COMPLETED' | 'IN_PROGRESS' | 'FAILED'
export type RunPhase =
  | 'INITIALIZING'
  | 'RESEARCHING'
  | 'DECIDING'
  | 'TRADING'
  | 'COMPLETED'
  | 'ERROR'
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
}

export interface Agent {
  id: number
  name: string
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

export interface ResearchPhase {
  researchId: number
  candidates: string[]
  sources: Source[]
  researchNotes: string
  toolCalls: ToolCall[]
  latencyMs: number
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
}

export interface ExecutionPhase {
  executionId: number
  tradeId: number | null
  status: string
  errorDetails: string | null
}

export interface RunDetailResponse {
  run: TradingRun
  research: ResearchPhase | null
  decision: DecisionPhase | null
  execution: ExecutionPhase | null
}
