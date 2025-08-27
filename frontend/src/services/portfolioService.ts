import { apiClient } from './api';

// Types for portfolio history
export interface PortfolioHistoryPoint {
  timestamp: string;
  portfolioValue: number;
}

// Portfolio API functions
export const portfolioService = {
  // Get portfolio history for a specific agent
  getPortfolioHistory: async (agentName: string, days: number = 7): Promise<PortfolioHistoryPoint[]> => {
    const response = await apiClient.get(`/accounts/portfolio/${agentName}/history?days=${days}`);
    return response.data || [];
  },
};