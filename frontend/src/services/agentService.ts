import { apiClient } from './api';

// Types for agent detail
export interface PortfolioInfo {
  cashBalance: number;
  holdings: { [symbol: string]: number };
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
  name: string;
  strategy: string;
  initialCapital: number;
  portfolio: PortfolioInfo;
  recentRuns: RunSummary[];
}

export interface AgentRun {
  id: number;
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
  getAgentDetail: async (agentName: string): Promise<AgentDetail> => {
    const response = await apiClient.get(`/agents/${agentName}`);
    return response.data;
  },

  // Get agent runs history
  getAgentRuns: async (agentName: string, limit: number = 10): Promise<AgentRun[]> => {
    const response = await apiClient.get(`/agents/${agentName}/runs`, {
      params: { limit }
    });
    return response.data;
  },
};
