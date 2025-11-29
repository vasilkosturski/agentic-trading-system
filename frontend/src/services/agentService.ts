import { apiClient } from './api';

// Types for agent detail
export interface HoldingDto {
  symbol: string;
  quantity: number;
  averagePrice: number | null;
}

export interface PortfolioInfo {
  cashBalance: number;
  holdings: HoldingDto[];
  totalValue: number;
  totalReturn: number;
  totalReturnPercent: number;
}

export interface RunSummary {
  id: number;
  runType: string;
  outcome: string;
  timestamp: string;
  tradeCount: number;
  summary: string | null;
}

export interface AgentDetail {
  id: number;
  name: string;
  strategy: string;
  initialCapital: number;
  portfolio: PortfolioInfo;
  recentRuns: RunSummary[];
}

export interface AgentRun {
  id: number;
  agentId: number | null;
  agentName: string;
  runType: string;
  startTime: string;
  endTime: string | null;
  outcome: string;
  fullReasoning: string | null;
  researchSources: string | null;
  summary: string | null;
  tradeCount: number;
  errorMessage: string | null;
  agentContext: string | null;
  marketConditions: string | null;
  durationSeconds: number | null;
}

// Agent API functions
export const agentService = {
  // Get agent detail with portfolio and recent runs
  getAgentDetail: async (agentId: number): Promise<AgentDetail> => {
    const response = await apiClient.get(`/agents/${agentId}`);
    return response.data;
  },

  // Get agent runs history
  getAgentRuns: async (agentId: number, limit: number = 10): Promise<AgentRun[]> => {
    const response = await apiClient.get(`/agents/${agentId}/runs`, {
      params: { limit }
    });
    return response.data;
  },
};
