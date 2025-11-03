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
    try {
      const response = await apiClient.post('/trading/run-cycle');
      
      // Handle ToolResponse wrapper format (202 Accepted)
      if (response.data && response.data.success && response.data.data) {
        return response.data.data;
      }
      
      throw { reason: 'UNKNOWN', message: 'Unexpected response format' };
    } catch (error: any) {
      // Handle HTTP error responses (409 Conflict, 500 Error, etc.)
      if (error.response) {
        const status = error.response.status;
        const data = error.response.data;
        
        // Extract error message from ToolResponse wrapper or direct error
        const errorMessage = data?.error || data?.message || 'Failed to trigger trading cycle';
        const reason = status === 409 ? 'MARKET_CLOSED' : 'SERVICE_ERROR';
        
        const errorData: TriggerCycleError = {
          reason: reason,
          message: errorMessage
        };
        throw errorData;
      }
      
      // Network error or other issue
      throw {
        reason: 'NETWORK_ERROR',
        message: error.message || 'Failed to connect to server'
      };
    }
  },
};