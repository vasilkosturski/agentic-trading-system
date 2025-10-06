import { useTradingAgents, useMarketStatus } from '../../hooks';
import SimplePortfolioChart from './SimplePortfolioChart';
import RecentTrades from './RecentTrades';

const TradingDashboard = () => {
  const { data: agents, isLoading, error, isError } = useTradingAgents();
  const { data: marketStatus, isLoading: marketStatusLoading } = useMarketStatus();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="text-center py-12">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            Trading Dashboard
          </h2>
          <div className="flex justify-center items-center space-x-2">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="text-lg text-gray-600 dark:text-gray-300">
              Loading trading agents...
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-6">
        <div className="text-center py-12">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            Trading Dashboard
          </h2>
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 max-w-md mx-auto">
            <div className="flex items-center space-x-2 text-red-600 dark:text-red-400 mb-2">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span className="font-medium">Connection Error</span>
            </div>
            <p className="text-sm text-red-600 dark:text-red-400 mb-4">
              Unable to connect to the trading backend. Please check if the server is running.
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Error: {error?.message || 'Unknown error occurred'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercent = (value: number | undefined) => {
    if (value === undefined || value === null) return '0.00%';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  return (
    <div className="space-y-6">
      <div className="text-center py-8">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
          Trading Dashboard
        </h2>
        <div className="flex items-center justify-center space-x-4 mb-8">
          <p className="text-lg text-gray-600 dark:text-gray-300">
            4 Autonomous Traders: Warren, George, Ray, and Cathie
          </p>
          {!marketStatusLoading && marketStatus && (
            <div className="flex flex-col items-start">
              <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-sm font-medium ${
                marketStatus.status === 'OPEN'
                  ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                  : 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
              }`}>
                <div className={`w-2 h-2 rounded-full ${
                  marketStatus.status === 'OPEN' ? 'bg-green-500' : 'bg-red-500'
                }`}></div>
                <span>Market {marketStatus.status === 'OPEN' ? 'Open' : 'Closed'}</span>
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Next: {marketStatus.nextEvent} • As of {new Date(marketStatus.currentTime).toLocaleTimeString()}
              </div>
            </div>
          )}
        </div>
        
        {/* 4-trader grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 max-w-7xl mx-auto">
          {agents?.map((agent) => (
            <div key={agent.agentName} className="trading-card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="trader-header">{agent.agentName}</h3>
                <div className={`flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium ${
                  agent.active
                    ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                    : 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'
                }`}>
                  <div className={`w-1.5 h-1.5 rounded-full ${
                    agent.active ? 'bg-green-500' : 'bg-gray-500'
                  }`}></div>
                  <span>{agent.active ? 'Active' : 'Inactive'}</span>
                </div>
              </div>
              
              <div className="space-y-4">
                <div className="text-center">
                  <div className={`text-2xl font-bold ${
                    agent.dayPnL >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {formatCurrency(agent.portfolioValue)}
                  </div>
                  <div className="text-sm text-gray-500 mb-2">
                    Portfolio Value
                  </div>
                  <div className={`text-sm font-medium ${
                    agent.dayPnL >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {formatCurrency(agent.dayPnL)} ({formatPercent(agent.dayPnLPercent)})
                  </div>
                  <div className="text-xs text-gray-400">
                    Today's P&L
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="text-center">
                    <div className="font-semibold text-gray-900 dark:text-white">
                      {agent.totalTrades}
                    </div>
                    <div className="text-gray-500">Total Trades</div>
                  </div>
                  <div className="text-center">
                    <div className={`font-semibold ${
                      (agent.totalReturnPercent ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {formatPercent(agent.totalReturnPercent)}
                    </div>
                    <div className="text-gray-500">Total Return</div>
                  </div>
                </div>
                
                <div className="text-center">
                  <div className="font-semibold text-gray-900 dark:text-white">
                    {agent.currentPositions}
                  </div>
                  <div className="text-xs text-gray-500">Current Positions</div>
                </div>
                
                {/* Portfolio Value Chart */}
                <div className="mt-4 border-t border-gray-200 dark:border-gray-700 pt-4">
                  <div className="text-xs text-gray-500 mb-2 text-center">7-Day Portfolio Value</div>
                  <SimplePortfolioChart agentName={agent.agentName} />
                </div>
                
                <div className="text-xs text-gray-400 text-center">
                  Last Activity: {new Date(agent.lastActivity).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
        </div>
        
        {/* Recent Trades Section */}
        <div className="mt-12 max-w-7xl mx-auto">
          <RecentTrades />
        </div>
        
        <div className="mt-8 text-sm text-gray-500">
          <div className="flex items-center justify-center space-x-4">
            <span>✅ API Integration Complete</span>
            <span>•</span>
            <span>Real-time data updates every 15 seconds</span>
            <span>•</span>
            <span>Connected to Java Spring Boot backend</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TradingDashboard;