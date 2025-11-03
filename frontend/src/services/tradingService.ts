import { apiClient } from './api';

// Types for agent status (only what's actually used)
export interface AgentStatus {
  agentId: number;
  agentName: string;
  active: boolean;
  lastActivity: string;
  totalTrades: number;
  totalReturnPercent: number;
  portfolioValue: number;
  dayPnL: number;
  dayPnLPercent: number;
  currentPositions: number;
  cycleIntervalSeconds?: number;
}

export interface TriggerCycleResponse {
  message: string;
  timestamp?: string;
}

export interface TriggerCycleError {
  reason: string;
  message: string;
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
  
  // Trigger a manual trading cycle
  triggerManualCycle: async (): Promise<TriggerCycleResponse> => {
    const response = await apiClient.post('/trading/run-cycle');
    
    // Handle ToolResponse wrapper format
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    
    // Handle error case (e.g., market closed)
    if (response.data && !response.data.success) {
      const errorData: TriggerCycleError = {
        reason: response.data.data?.reason || 'UNKNOWN',
        message: response.data.error || 'Failed to trigger trading cycle'
      };
      throw errorData;
    }
    
    throw { reason: 'UNKNOWN', message: 'Unexpected response format' };
  },
};