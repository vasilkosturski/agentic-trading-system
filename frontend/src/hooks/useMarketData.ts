import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { marketService } from '../services';

// Query keys for market data
export const marketKeys = {
  all: ['market'] as const,
  quotes: () => [...marketKeys.all, 'quotes'] as const,
  quote: (symbol: string) => [...marketKeys.quotes(), symbol] as const,
  multiQuotes: (symbols: string[]) => [...marketKeys.quotes(), 'multi', symbols.sort()] as const,
  history: () => [...marketKeys.all, 'history'] as const,
  historicalData: (symbol: string, period: string, interval: string) => 
    [...marketKeys.history(), symbol, period, interval] as const,
  status: () => [...marketKeys.all, 'status'] as const,
  search: () => [...marketKeys.all, 'search'] as const,
  trending: () => [...marketKeys.all, 'trending'] as const,
  watchlist: () => [...marketKeys.all, 'watchlist'] as const,
  quality: (symbol: string) => [...marketKeys.all, 'quality', symbol] as const,
};

// Hook to get market data for a single symbol
export const useMarketData = (symbol: string) => {
  return useQuery({
    queryKey: marketKeys.quote(symbol),
    queryFn: () => marketService.getMarketData(symbol),
    enabled: !!symbol,
    staleTime: 15 * 1000, // 15 seconds for real-time data
    refetchInterval: 15 * 1000, // Auto-refresh every 15 seconds
    retry: 3,
  });
};

// Hook to get market data for multiple symbols
export const useMultipleMarketData = (symbols: string[]) => {
  return useQuery({
    queryKey: marketKeys.multiQuotes(symbols),
    queryFn: () => marketService.getMultipleMarketData(symbols),
    enabled: symbols.length > 0,
    staleTime: 15 * 1000,
    refetchInterval: 15 * 1000,
    retry: 2,
  });
};

// Hook to get historical data
export const useHistoricalData = (
  symbol: string,
  period: '1d' | '5d' | '1mo' | '3mo' | '6mo' | '1y' | '2y' | '5y' | '10y' | 'ytd' | 'max',
  interval: '1m' | '2m' | '5m' | '15m' | '30m' | '60m' | '90m' | '1h' | '1d' | '5d' | '1wk' | '1mo' | '3mo'
) => {
  return useQuery({
    queryKey: marketKeys.historicalData(symbol, period, interval),
    queryFn: () => marketService.getHistoricalData(symbol, period, interval),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000, // 5 minutes for historical data
    retry: 2,
  });
};

// Hook to get market status
export const useMarketStatus = () => {
  return useQuery({
    queryKey: marketKeys.status(),
    queryFn: marketService.getMarketStatus,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 60 * 1000, // Check market status every minute
  });
};

// Hook to search symbols
export const useSymbolSearch = (query: string) => {
  return useQuery({
    queryKey: [...marketKeys.search(), query],
    queryFn: () => marketService.searchSymbols(query),
    enabled: query.length >= 2, // Only search if query is at least 2 characters
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// Hook to get trending symbols
export const useTrendingSymbols = () => {
  return useQuery({
    queryKey: marketKeys.trending(),
    queryFn: marketService.getTrendingSymbols,
    staleTime: 15 * 60 * 1000, // 15 minutes
    refetchInterval: 15 * 60 * 1000,
  });
};

// Hook to get watchlist
export const useWatchlist = () => {
  return useQuery({
    queryKey: marketKeys.watchlist(),
    queryFn: marketService.getWatchlist,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

// Hook to add symbol to watchlist
export const useAddToWatchlist = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ symbol, name }: { symbol: string; name: string }) =>
      marketService.addToWatchlist(symbol, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: marketKeys.watchlist() });
    },
  });
};

// Hook to remove symbol from watchlist
export const useRemoveFromWatchlist = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: marketService.removeFromWatchlist,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: marketKeys.watchlist() });
    },
  });
};

// Hook to get data quality info
export const useDataQuality = (symbol: string) => {
  return useQuery({
    queryKey: marketKeys.quality(symbol),
    queryFn: () => marketService.getDataQuality(symbol),
    enabled: !!symbol,
    staleTime: 60 * 1000, // 1 minute
  });
};

// Custom hook for real-time market data with WebSocket-like behavior
export const useRealTimeMarketData = (symbols: string[]) => {
  const query = useMultipleMarketData(symbols);
  
  return {
    ...query,
    // Add helper methods for real-time data
    isStale: query.dataUpdatedAt < Date.now() - 30 * 1000, // Data older than 30 seconds
    lastUpdate: query.dataUpdatedAt,
    nextUpdate: query.dataUpdatedAt + 15 * 1000, // Next expected update
  };
};