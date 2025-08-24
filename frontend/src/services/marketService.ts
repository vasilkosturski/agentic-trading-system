import { apiClient } from './api';

// Types for market data - only what's actually used
export interface MarketStatus {
  isOpen: boolean;
  nextOpen: string;
  nextClose: string;
  timezone: string;
}

// Market data API functions - only what's actually used
export const marketService = {
  // Get market status - the only function actually used
  getMarketStatus: async (): Promise<MarketStatus> => {
    const response = await apiClient.get('/market/status');
    return response.data;
  },
};