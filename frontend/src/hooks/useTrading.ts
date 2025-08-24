import { useQuery } from '@tanstack/react-query';
import { tradingService } from '../services';

// Query keys for trading data - only what's actually used
export const tradingKeys = {
  all: ['trading'] as const,
  agents: () => [...tradingKeys.all, 'agents'] as const,
  allAgentsStatus: () => [...tradingKeys.agents(), 'status'] as const,
};

// Hook to get all agents status - the only hook actually used
export const useAllAgentsStatus = () => {
  return useQuery({
    queryKey: tradingKeys.allAgentsStatus(),
    queryFn: tradingService.getAllAgentsStatus,
    staleTime: 15 * 1000,
    refetchInterval: 15 * 1000,
  });
};

// Custom hook for the 4 main trading agents - the main hook used by TradingDashboard
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