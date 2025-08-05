import { apiClient } from './api';

// Types for market data
export interface MarketData {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  high: number;
  low: number;
  open: number;
  previousClose: number;
  timestamp: string;
  source: string;
  quality: 'REAL_TIME' | 'DELAYED' | 'CACHED';
}

export interface HistoricalData {
  symbol: string;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface MarketStatus {
  isOpen: boolean;
  nextOpen: string;
  nextClose: string;
  timezone: string;
}

export interface WatchlistItem {
  id: string;
  symbol: string;
  name: string;
  addedAt: string;
}

// Market data API functions
export const marketService = {
  // Get current market data for a symbol
  getMarketData: async (symbol: string): Promise<MarketData> => {
    const response = await apiClient.get(`/market/quote/${symbol}`);
    return response.data;
  },

  // Get market data for multiple symbols
  getMultipleMarketData: async (symbols: string[]): Promise<MarketData[]> => {
    const response = await apiClient.post('/market/quotes', { symbols });
    return response.data;
  },

  // Get historical data
  getHistoricalData: async (
    symbol: string,
    period: '1d' | '5d' | '1mo' | '3mo' | '6mo' | '1y' | '2y' | '5y' | '10y' | 'ytd' | 'max',
    interval: '1m' | '2m' | '5m' | '15m' | '30m' | '60m' | '90m' | '1h' | '1d' | '5d' | '1wk' | '1mo' | '3mo'
  ): Promise<HistoricalData[]> => {
    const response = await apiClient.get(`/market/history/${symbol}`, {
      params: { period, interval }
    });
    return response.data;
  },

  // Get market status
  getMarketStatus: async (): Promise<MarketStatus> => {
    const response = await apiClient.get('/market/status');
    return response.data;
  },

  // Search for symbols
  searchSymbols: async (query: string): Promise<{ symbol: string; name: string; type: string }[]> => {
    const response = await apiClient.get('/market/search', {
      params: { q: query }
    });
    return response.data;
  },

  // Get trending symbols
  getTrendingSymbols: async (): Promise<string[]> => {
    const response = await apiClient.get('/market/trending');
    return response.data;
  },

  // Watchlist management
  getWatchlist: async (): Promise<WatchlistItem[]> => {
    const response = await apiClient.get('/market/watchlist');
    return response.data;
  },

  addToWatchlist: async (symbol: string, name: string): Promise<WatchlistItem> => {
    const response = await apiClient.post('/market/watchlist', { symbol, name });
    return response.data;
  },

  removeFromWatchlist: async (watchlistId: string): Promise<void> => {
    await apiClient.delete(`/market/watchlist/${watchlistId}`);
  },

  // Get market data quality info
  getDataQuality: async (symbol: string): Promise<{
    symbol: string;
    lastUpdate: string;
    source: string;
    quality: string;
    delay: number;
  }> => {
    const response = await apiClient.get(`/market/quality/${symbol}`);
    return response.data;
  },
};