import { apiClient } from './api';

// Types for agent status (only what's actually used)
export interface AgentStatus {
  agentName: string;
  isActive: boolean;
  lastActivity: string;
  totalTrades: number;
  totalReturnPercent: number;
  portfolioValue: number;
  dayPnL: number;
  dayPnLPercent: number;
  currentPositions: number;
}

// Trading API functions - only what's actually used
export const tradingService = {
  // Get all agents status - the only function actually used
  getAllAgentsStatus: async (): Promise<AgentStatus[]> => {
    const response = await apiClient.get('/trading/agents/status');
    // Handle ToolResponse wrapper format
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    // Fallback to direct data if not wrapped
    return response.data || [];
  },
};