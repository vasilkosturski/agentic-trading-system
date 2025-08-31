// Export only the hooks that are actually used
export * from './useMarketData';
export * from './useTrading';
export * from './usePortfolioHistory';

// Re-export specific hooks for easier importing
export { useTradingAgents } from './useTrading';
export { useMarketStatus } from './useMarketData';