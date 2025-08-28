import { apiClient } from './api';

export interface RecentTrade {
  agentName: string;
  transactionType: 'BUY' | 'SELL';
  symbol: string;
  quantity: number;
  price: number;
  totalAmount: number;
  timestamp: string;
  rationale: string;
}

export const tradesService = {
  /**
   * Get recent trades across all agents
   */
  async getRecentTrades(limit: number = 20): Promise<RecentTrade[]> {
    const response = await apiClient.get<RecentTrade[]>(`/accounts/trades/recent?limit=${limit}`);
    return response.data;
  }
};