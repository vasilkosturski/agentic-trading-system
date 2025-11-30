import { apiClient } from './api';

export interface TradeInfo {
  id: number;
  symbol: string;
  quantity: number;
  price: number;
  timestamp: string;
  // Note: rationale removed - reasoning is stored on AgentRun, not on individual transactions
  transactionType: string; // BUY or SELL
  totalAmount: number;
}

export interface ToolCallInfo {
  id: number;
  toolName: string;
  inputParams: string | null; // JSON string
  outputResult: string | null; // JSON string or text
  timestamp: string;
  durationMs: number | null;
  success: boolean;
  errorMessage: string | null;
  sequenceNumber: number;
}

export interface ReasoningStepInfo {
  id: number;
  stepType: string; // e.g., "initialization", "research", "analysis", "decision", "execution"
  stepDescription: string;
  reasoningText: string;
  timestamp: string;
  sequenceNumber: number;
}

export interface RunDetail {
  id: number;
  agentId: number;
  agentName: string;
  runType: string;
  startTime: string;
  endTime: string | null;
  outcome: string;
  summary: string | null; // Simple summary (brief explanation)
  fullReasoning: string | null; // Full detailed reasoning
  researchSources: string | null; // JSON string array of web sources
  historicalContext: string | null; // JSON object with historical insights (past trades, agent context)
  tradeCount: number;
  errorMessage: string | null;
  // Note: agentContext removed - merged into historicalContext
  marketConditions: string | null; // JSON string
  durationSeconds: number | null;
  trades: TradeInfo[];
  toolCalls?: ToolCallInfo[]; // Agent transparency: tool calls
  reasoningSteps?: ReasoningStepInfo[]; // Agent transparency: reasoning steps
}

export const runService = {
  getRunDetail: async (runId: number): Promise<RunDetail> => {
    const response = await apiClient.get(`/runs/${runId}`);
    return response.data;
  },
};
