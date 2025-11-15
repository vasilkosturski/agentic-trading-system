import { apiClient } from './api';

export interface TradeInfo {
  id: number;
  symbol: string;
  quantity: number;
  price: number;
  timestamp: string;
  rationale: string | null;
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
  fullReasoning: string | null;
  researchSources: string | null; // JSON string
  summary: string | null;
  tradeCount: number;
  errorMessage: string | null;
  agentContext: string | null; // JSON string
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
