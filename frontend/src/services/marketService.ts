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
    const payload = response.data;
    // Handle ToolResponse wrapper from backend when present
    if (payload && typeof payload === 'object' && 'success' in payload) {
      if (payload.success && payload.data) {
        return payload.data as MarketStatus;
      }
      // If backend indicates failure, throw with message to surface error state
      throw new Error((payload as any).error || 'Failed to fetch market status');
    }
    // Fallback: if no wrapper, assume direct MarketStatus
    return payload as MarketStatus;
  },
};