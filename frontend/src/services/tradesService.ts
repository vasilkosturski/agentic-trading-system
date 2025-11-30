import { apiClient } from './api';
import { ReasoningStep } from '../components/shared/AgentReasoningTimeline';

export interface RecentTrade {
  id: number;
  agentName: string;
  transactionType: 'BUY' | 'SELL';
  symbol: string;
  quantity: number;
  price: number;
  totalAmount: number;
  timestamp: string;
  // Note: rationale removed - reasoning is stored on AgentRun, not on individual transactions
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
    // Note: rationale removed - reasoning is stored on AgentRun, not on individual transactions
  };
  // All reasoning fields come from the AgentRun that created this trade:
  summary?: string; // Simple summary (brief explanation)
  fullReasoning?: string; // Full detailed reasoning
  researchSources?: string; // JSON string array of web sources
  historicalContext?: string; // JSON object with historical insights (past trades, agent context)
  // Note: agentContext removed - merged into historicalContext
  relatedTrades?: Array<{
    id: number;
    type: 'BUY' | 'SELL';
    quantity: number;
    price: number;
    timestamp: string;
  }>;
  runId?: number | null; // ID of the agent run that created this trade
  runSummary?: string | null; // Summary of the run that created this trade
  reasoningSteps?: ReasoningStep[]; // Agent reasoning timeline
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
  async getAgentTrades(agentId: number): Promise<RecentTrade[]> {
    const response = await apiClient.get<{ data: any[] }>(`/trading/agent-trades?agentId=${agentId}`);
    // Map API response to RecentTrade interface
    return response.data.data.map((trade: any) => ({
      id: parseInt(trade.id),
      agentName: trade.agentName,
      transactionType: trade.type as 'BUY' | 'SELL',
      symbol: trade.symbol,
      quantity: trade.quantity,
      price: trade.price,
      totalAmount: trade.price * trade.quantity,
      timestamp: trade.timestamp
      // Note: rationale removed - trades no longer have individual rationale
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