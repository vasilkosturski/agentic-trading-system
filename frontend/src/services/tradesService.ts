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
  runId?: number | null; // ID of the agent run that created this trade
  runSummary?: string | null; // Summary of the run that created this trade
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
   * Get trades for a specific agent
   */
  async getAgentTrades(agentName: string): Promise<RecentTrade[]> {
    const response = await apiClient.get<{ data: any[] }>(`/trading/agent-trades?agentName=${agentName}`);
    // Map API response to RecentTrade interface
    return response.data.data.map((trade: any) => ({
      id: parseInt(trade.id),
      agentName: trade.agentName,
      transactionType: trade.type as 'BUY' | 'SELL',
      symbol: trade.symbol,
      quantity: trade.quantity,
      price: trade.price,
      totalAmount: trade.price * trade.quantity,
      timestamp: trade.timestamp,
      rationale: trade.reasoning || ''
    }));
  },

  /**
   * Get detailed information about a specific trade
   */
  async getTradeDetail(tradeId: number): Promise<TradeDetail> {
    const response = await apiClient.get<TradeDetail>(`/accounts/trades/${tradeId}`);
    return response.data;
  }
};