import { apiClient } from './api';

// Types for trading operations
export interface TradeOrder {
  id: string;
  accountId: string;
  symbol: string;
  type: 'BUY' | 'SELL';
  orderType: 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT';
  quantity: number;
  price?: number;
  stopPrice?: number;
  timeInForce: 'DAY' | 'GTC' | 'IOC' | 'FOK';
  status: 'PENDING' | 'FILLED' | 'PARTIALLY_FILLED' | 'CANCELLED' | 'REJECTED';
  filledQuantity: number;
  averageFillPrice: number;
  createdAt: string;
  updatedAt: string;
  agentId?: string; // For autonomous agent trades
}

export interface CreateOrderRequest {
  accountId: string;
  symbol: string;
  type: 'BUY' | 'SELL';
  orderType: 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT';
  quantity: number;
  price?: number;
  stopPrice?: number;
  timeInForce?: 'DAY' | 'GTC' | 'IOC' | 'FOK';
  agentId?: string;
}

export interface AgentTrade {
  id: string;
  agentName: string;
  accountId: string;
  symbol: string;
  type: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  reasoning: string;
  confidence: number;
  timestamp: string;
  status: 'EXECUTED' | 'PENDING' | 'FAILED';
  orderId?: string;
}

export interface AgentStatus {
  agentName: string;
  isActive: boolean;
  lastActivity: string;
  totalTrades: number;
  successRate: number;
  portfolioValue: number;
  dayPnL: number;
  dayPnLPercent: number;
  currentPositions: number;
}

export interface TradingStats {
  totalTrades: number;
  successfulTrades: number;
  failedTrades: number;
  totalVolume: number;
  totalPnL: number;
  winRate: number;
  averageTradeSize: number;
  largestWin: number;
  largestLoss: number;
}

// Trading API functions
export const tradingService = {
  // Order management
  createOrder: async (orderData: CreateOrderRequest): Promise<TradeOrder> => {
    const response = await apiClient.post('/trading/orders', orderData);
    // Handle ToolResponse wrapper format
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    return response.data;
  },

  getOrders: async (accountId?: string): Promise<TradeOrder[]> => {
    const params = accountId ? { accountId } : {};
    const response = await apiClient.get('/trading/orders', { params });
    // Handle ToolResponse wrapper format
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    return response.data || [];
  },

  getOrder: async (orderId: string): Promise<TradeOrder> => {
    const response = await apiClient.get(`/trading/orders/${orderId}`);
    // Handle ToolResponse wrapper format
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    return response.data;
  },

  cancelOrder: async (orderId: string): Promise<void> => {
    await apiClient.delete(`/trading/orders/${orderId}`);
  },

  // Agent trading operations
  getAgentTrades: async (agentName?: string): Promise<AgentTrade[]> => {
    const params = agentName ? { agentName } : {};
    const response = await apiClient.get('/trading/agent-trades', { params });
    // Handle ToolResponse wrapper format
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    return response.data || [];
  },

  getAgentStatus: async (agentName: string): Promise<AgentStatus> => {
    const response = await apiClient.get(`/trading/agents/${agentName}/status`);
    // Handle ToolResponse wrapper format
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    // Fallback to direct data if not wrapped
    return response.data;
  },

  getAllAgentsStatus: async (): Promise<AgentStatus[]> => {
    const response = await apiClient.get('/trading/agents/status');
    // Handle ToolResponse wrapper format
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    // Fallback to direct data if not wrapped
    return response.data || [];
  },

  // Start/stop agent trading
  startAgent: async (agentName: string): Promise<void> => {
    await apiClient.post(`/trading/agents/${agentName}/start`);
  },

  stopAgent: async (agentName: string): Promise<void> => {
    await apiClient.post(`/trading/agents/${agentName}/stop`);
  },

  // Trading statistics
  getTradingStats: async (accountId?: string, agentName?: string): Promise<TradingStats> => {
    const params: any = {};
    if (accountId) params.accountId = accountId;
    if (agentName) params.agentName = agentName;
    
    const response = await apiClient.get('/trading/stats', { params });
    // Handle ToolResponse wrapper format
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    return response.data;
  },

  // Portfolio performance
  getPortfolioPerformance: async (
    accountId: string,
    period: '1d' | '1w' | '1m' | '3m' | '6m' | '1y' | 'ytd' | 'all'
  ): Promise<{
    timestamps: string[];
    values: number[];
    returns: number[];
    benchmark?: number[];
  }> => {
    const response = await apiClient.get(`/trading/performance/${accountId}`, {
      params: { period }
    });
    return response.data;
  },

  // Risk metrics
  getRiskMetrics: async (accountId: string): Promise<{
    totalExposure: number;
    maxDrawdown: number;
    sharpeRatio: number;
    volatility: number;
    beta: number;
    var95: number; // Value at Risk 95%
    expectedShortfall: number;
  }> => {
    const response = await apiClient.get(`/trading/risk/${accountId}`);
    return response.data;
  },

  // Real-time trading activity
  getRecentActivity: async (limit: number = 50): Promise<AgentTrade[]> => {
    const response = await apiClient.get('/trading/activity', {
      params: { limit }
    });
    // Handle ToolResponse wrapper format
    if (response.data && response.data.success && response.data.data) {
      return response.data.data;
    }
    return response.data || [];
  },
};