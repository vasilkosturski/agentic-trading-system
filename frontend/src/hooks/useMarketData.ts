import { useQuery } from '@tanstack/react-query';
import { marketService } from '../services';

// Query keys for market data - only what's actually used
export const marketKeys = {
  all: ['market'] as const,
  status: () => [...marketKeys.all, 'status'] as const,
};

// Hook to get market status - the only hook actually used
export const useMarketStatus = () => {
  return useQuery({
    queryKey: marketKeys.status(),
    queryFn: marketService.getMarketStatus,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 60 * 1000, // Check market status every minute
  });
};