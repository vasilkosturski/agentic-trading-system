import { useQuery } from '@tanstack/react-query';
import { portfolioService, PortfolioHistoryPoint } from '../services/portfolioService';

// Query keys for portfolio history data
export const portfolioKeys = {
  all: ['portfolio'] as const,
  history: () => [...portfolioKeys.all, 'history'] as const,
  agentHistory: (agentId: number, days: number) => [...portfolioKeys.history(), agentId, days] as const,
};

// Hook to get portfolio history for a specific agent
export const usePortfolioHistory = (agentId: number, days: number = 7) => {
  return useQuery({
    queryKey: portfolioKeys.agentHistory(agentId, days),
    queryFn: () => portfolioService.getPortfolioHistory(agentId, days),
    staleTime: 60 * 1000, // 1 minute - portfolio history doesn't change as frequently
    refetchInterval: 60 * 1000, // Refetch every minute
    enabled: typeof agentId === 'number' && !Number.isNaN(agentId),
    select: (data: PortfolioHistoryPoint[]) => {
      // Transform data for Recharts - ensure we have valid data points
      return data.map(point => ({
        timestamp: new Date(point.timestamp).getTime(), // Convert to timestamp for chart
        portfolioValue: point.portfolioValue || 0,
        formattedTime: new Date(point.timestamp).toLocaleTimeString('en-US', { 
          hour: '2-digit', 
          minute: '2-digit' 
        }),
      }));
    },
  });
};