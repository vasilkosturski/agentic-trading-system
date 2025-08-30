import { apiClient } from './api';

// Types for market data - matching backend API response
export interface MarketStatus {
  status: string; // "OPEN" or "CLOSED"
  nextEvent: string; // e.g., "Market opens at 9:30 AM ET"
  currentTime: string; // ISO timestamp
}

// Market data API functions - only what's actually used
export const marketService = {
  // Get market status - the only function actually used
  getMarketStatus: async (): Promise<MarketStatus> => {
    const response = await apiClient.get('/market/status');
    return response.data;
  },
};