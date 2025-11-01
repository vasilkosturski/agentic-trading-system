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
}

export const runService = {
  getRunDetail: async (runId: number): Promise<RunDetail> => {
    const response = await apiClient.get(`/runs/${runId}`);
    return response.data;
  },
};
