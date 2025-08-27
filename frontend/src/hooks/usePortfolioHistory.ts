import { useQuery } from '@tanstack/react-query';
import { portfolioService, PortfolioHistoryPoint } from '../services/portfolioService';

// Query keys for portfolio history data
export const portfolioKeys = {
  all: ['portfolio'] as const,
  history: () => [...portfolioKeys.all, 'history'] as const,
  agentHistory: (agentName: string, days: number) => [...portfolioKeys.history(), agentName, days] as const,
};

// Hook to get portfolio history for a specific agent
export const usePortfolioHistory = (agentName: string, days: number = 7) => {
  return useQuery({
    queryKey: portfolioKeys.agentHistory(agentName, days),
    queryFn: () => portfolioService.getPortfolioHistory(agentName, days),
    staleTime: 60 * 1000, // 1 minute - portfolio history doesn't change as frequently
    refetchInterval: 60 * 1000, // Refetch every minute
    enabled: !!agentName, // Only run query if agentName is provided
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