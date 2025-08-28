import { useState, useEffect } from 'react';
import { tradesService, RecentTrade } from '../services/tradesService';

export const useRecentTrades = (limit: number = 20, refreshInterval: number = 15000) => {
  const [trades, setTrades] = useState<RecentTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTrades = async () => {
    try {
      setError(null);
      const data = await tradesService.getRecentTrades(limit);
      setTrades(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch recent trades');
      console.error('Error fetching recent trades:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrades();

    // Set up auto-refresh
    const interval = setInterval(fetchTrades, refreshInterval);

    return () => clearInterval(interval);
  }, [limit, refreshInterval]);

  return {
    trades,
    loading,
    error,
    refetch: fetchTrades
  };
};