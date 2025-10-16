import { apiClient } from './api';

export interface RecentTrade {
  id: number;
  agentName: string;
  transactionType: 'BUY' | 'SELL';
  symbol: string;
  quantity: number;
  price: number;
  totalAmount: number;
  timestamp: string;
  rationale: string;
}

export interface TradeDetail {
  trade: {
    id: number;
    agentName: string;
    type: 'BUY' | 'SELL';
    symbol: string;
    quantity: number;
    price: number;
    totalValue: number;
    timestamp: string;
    rationale: string;
  };
  fullReasoning?: string;
  researchSources?: string; // JSON string
  agentContext?: string; // JSON string
  relatedTrades?: Array<{
    id: number;
    type: 'BUY' | 'SELL';
    quantity: number;
    price: number;
    timestamp: string;
  }>;
}

export const tradesService = {
  /**
   * Get recent trades across all agents
   */
  async getRecentTrades(limit: number = 20): Promise<RecentTrade[]> {
    const response = await apiClient.get<RecentTrade[]>(`/accounts/trades/recent?limit=${limit}`);
    return response.data;
  },

  /**
   * Get detailed information about a specific trade
   */
  async getTradeDetail(tradeId: number): Promise<TradeDetail> {
    const response = await apiClient.get<TradeDetail>(`/accounts/trades/${tradeId}`);
    return response.data;
  }
};