import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  tradingService
} from '../services';

// Query keys for trading data
export const tradingKeys = {
  all: ['trading'] as const,
  orders: () => [...tradingKeys.all, 'orders'] as const,
  ordersList: (accountId?: string) => [...tradingKeys.orders(), { accountId }] as const,
  order: (orderId: string) => [...tradingKeys.orders(), orderId] as const,
  agentTrades: () => [...tradingKeys.all, 'agent-trades'] as const,
  agentTradesList: (agentName?: string) => [...tradingKeys.agentTrades(), { agentName }] as const,
  agents: () => [...tradingKeys.all, 'agents'] as const,
  agentStatus: (agentName: string) => [...tradingKeys.agents(), agentName, 'status'] as const,
  allAgentsStatus: () => [...tradingKeys.agents(), 'status'] as const,
  stats: () => [...tradingKeys.all, 'stats'] as const,
  tradingStats: (accountId?: string, agentName?: string) => 
    [...tradingKeys.stats(), { accountId, agentName }] as const,
  performance: (accountId: string, period: string) => 
    [...tradingKeys.all, 'performance', accountId, period] as const,
  risk: (accountId: string) => [...tradingKeys.all, 'risk', accountId] as const,
  activity: () => [...tradingKeys.all, 'activity'] as const,
};

// Hook to get orders
export const useOrders = (accountId?: string) => {
  return useQuery({
    queryKey: tradingKeys.ordersList(accountId),
    queryFn: () => tradingService.getOrders(accountId),
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 30 * 1000, // Auto-refresh every 30 seconds
  });
};

// Hook to get a specific order
export const useOrder = (orderId: string) => {
  return useQuery({
    queryKey: tradingKeys.order(orderId),
    queryFn: () => tradingService.getOrder(orderId),
    enabled: !!orderId,
    staleTime: 15 * 1000, // 15 seconds for active orders
    refetchInterval: 15 * 1000,
  });
};

// Hook to create an order
export const useCreateOrder = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: tradingService.createOrder,
    onSuccess: (data) => {
      // Invalidate orders list
      queryClient.invalidateQueries({ queryKey: tradingKeys.orders() });
      // Add the new order to cache
      queryClient.setQueryData(tradingKeys.order(data.id), data);
      // Invalidate agent trades and activity
      queryClient.invalidateQueries({ queryKey: tradingKeys.agentTrades() });
      queryClient.invalidateQueries({ queryKey: tradingKeys.activity() });
    },
  });
};

// Hook to cancel an order
export const useCancelOrder = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: tradingService.cancelOrder,
    onSuccess: (_, orderId) => {
      // Invalidate the specific order and orders list
      queryClient.invalidateQueries({ queryKey: tradingKeys.order(orderId) });
      queryClient.invalidateQueries({ queryKey: tradingKeys.orders() });
    },
  });
};

// Hook to get agent trades
export const useAgentTrades = (agentName?: string) => {
  return useQuery({
    queryKey: tradingKeys.agentTradesList(agentName),
    queryFn: () => tradingService.getAgentTrades(agentName),
    staleTime: 30 * 1000,
    refetchInterval: 30 * 1000,
  });
};

// Hook to get agent status
export const useAgentStatus = (agentName: string) => {
  return useQuery({
    queryKey: tradingKeys.agentStatus(agentName),
    queryFn: () => tradingService.getAgentStatus(agentName),
    enabled: !!agentName,
    staleTime: 15 * 1000,
    refetchInterval: 15 * 1000, // Frequent updates for agent status
  });
};

// Hook to get all agents status
export const useAllAgentsStatus = () => {
  return useQuery({
    queryKey: tradingKeys.allAgentsStatus(),
    queryFn: tradingService.getAllAgentsStatus,
    staleTime: 15 * 1000,
    refetchInterval: 15 * 1000,
  });
};

// Hook to start an agent
export const useStartAgent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: tradingService.startAgent,
    onSuccess: (_, agentName) => {
      // Invalidate agent status
      queryClient.invalidateQueries({ queryKey: tradingKeys.agentStatus(agentName) });
      queryClient.invalidateQueries({ queryKey: tradingKeys.allAgentsStatus() });
    },
  });
};

// Hook to stop an agent
export const useStopAgent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: tradingService.stopAgent,
    onSuccess: (_, agentName) => {
      // Invalidate agent status
      queryClient.invalidateQueries({ queryKey: tradingKeys.agentStatus(agentName) });
      queryClient.invalidateQueries({ queryKey: tradingKeys.allAgentsStatus() });
    },
  });
};

// Hook to get trading statistics
export const useTradingStats = (accountId?: string, agentName?: string) => {
  return useQuery({
    queryKey: tradingKeys.tradingStats(accountId, agentName),
    queryFn: () => tradingService.getTradingStats(accountId, agentName),
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchInterval: 2 * 60 * 1000,
  });
};

// Hook to get portfolio performance
export const usePortfolioPerformance = (
  accountId: string,
  period: '1d' | '1w' | '1m' | '3m' | '6m' | '1y' | 'ytd' | 'all'
) => {
  return useQuery({
    queryKey: tradingKeys.performance(accountId, period),
    queryFn: () => tradingService.getPortfolioPerformance(accountId, period),
    enabled: !!accountId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// Hook to get risk metrics
export const useRiskMetrics = (accountId: string) => {
  return useQuery({
    queryKey: tradingKeys.risk(accountId),
    queryFn: () => tradingService.getRiskMetrics(accountId),
    enabled: !!accountId,
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchInterval: 2 * 60 * 1000,
  });
};

// Hook to get recent trading activity
export const useRecentActivity = (limit: number = 50) => {
  return useQuery({
    queryKey: [...tradingKeys.activity(), { limit }],
    queryFn: () => tradingService.getRecentActivity(limit),
    staleTime: 15 * 1000,
    refetchInterval: 15 * 1000, // Real-time activity updates
  });
};

// Custom hook for the 4 main trading agents
export const useTradingAgents = () => {
  const agentNames = ['Warren', 'George', 'Ray', 'Cathie'];
  
  const agentsStatus = useQuery({
    queryKey: tradingKeys.allAgentsStatus(),
    queryFn: tradingService.getAllAgentsStatus,
    staleTime: 15 * 1000,
    refetchInterval: 15 * 1000,
    select: (data) => {
      // Ensure we have data for all 4 agents, with defaults if missing
      return agentNames.map(name => {
        const agentData = data.find(agent => agent.agentName === name);
        return agentData || {
          agentName: name,
          isActive: false,
          lastActivity: new Date().toISOString(),
          totalTrades: 0,
          successRate: 0,
          portfolioValue: 10000, // Default starting value
          dayPnL: 0,
          dayPnLPercent: 0,
          currentPositions: 0,
        };
      });
    },
  });

  return {
    ...agentsStatus,
    agents: agentsStatus.data || [],
  };
};