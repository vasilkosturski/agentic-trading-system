import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { agentService, type AgentDetail } from '../services/agentService';

const AgentDetailPage = () => {
  const { agentName } = useParams<{ agentName: string }>();

  const { data: agentDetail, isLoading, error } = useQuery<AgentDetail>({
    queryKey: ['agentDetail', agentName],
    queryFn: () => agentService.getAgentDetail(agentName!),
    enabled: !!agentName,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !agentDetail) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <p className="text-red-600 dark:text-red-400">
            Failed to load agent details. Agent not found or server error.
          </p>
          <Link to="/" className="text-blue-600 hover:underline mt-4 inline-block">
            ← Back to Dashboard
          </Link>
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

  const formatPercent = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Back Button */}
      <Link to="/" className="text-blue-600 hover:underline mb-4 inline-block">
        ← Back to Dashboard
      </Link>

      {/* Agent Header */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          {agentDetail.name}
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          {agentDetail.strategy}
        </p>
        <div className="text-sm text-gray-500">
          Initial Capital: {formatCurrency(agentDetail.initialCapital)}
        </div>
      </div>

      {/* Portfolio Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          Portfolio
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="text-center">
            <div className="text-sm text-gray-500 mb-1">Cash Balance</div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatCurrency(agentDetail.portfolio.cashBalance)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-sm text-gray-500 mb-1">Total Value</div>
            <div className={`text-2xl font-bold ${
              Math.abs(agentDetail.portfolio.totalReturnPercent) < 0.01
                ? 'text-gray-900 dark:text-white'
                : agentDetail.portfolio.totalReturnPercent >= 0
                ? 'text-green-600'
                : 'text-red-600'
            }`}>
              {formatCurrency(agentDetail.portfolio.totalValue)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-sm text-gray-500 mb-1">Total Return</div>
            <div className={`text-2xl font-bold ${
              Math.abs(agentDetail.portfolio.totalReturnPercent) < 0.01
                ? 'text-gray-600 dark:text-gray-400'
                : agentDetail.portfolio.totalReturnPercent >= 0
                ? 'text-green-600'
                : 'text-red-600'
            }`}>
              {formatPercent(agentDetail.portfolio.totalReturnPercent)}
            </div>
            <div className="text-sm text-gray-500">
              ({formatCurrency(agentDetail.portfolio.totalReturn)})
            </div>
          </div>
        </div>

        {/* Holdings */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
            Current Holdings
          </h3>
          {Object.keys(agentDetail.portfolio.holdings).length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(agentDetail.portfolio.holdings).map(([symbol, quantity]) => (
                <div key={symbol} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 text-center">
                  <div className="font-bold text-gray-900 dark:text-white">{symbol}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">{quantity} shares</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 dark:text-gray-400">No holdings</p>
          )}
        </div>
      </div>

      {/* Recent Runs Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          Recent Runs
        </h2>
        {agentDetail.recentRuns.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-gray-200 dark:border-gray-700">
                <tr className="text-left">
                  <th className="pb-3 text-sm font-medium text-gray-500 dark:text-gray-400">Time</th>
                  <th className="pb-3 text-sm font-medium text-gray-500 dark:text-gray-400">Type</th>
                  <th className="pb-3 text-sm font-medium text-gray-500 dark:text-gray-400">Outcome</th>
                  <th className="pb-3 text-sm font-medium text-gray-500 dark:text-gray-400">Trades</th>
                  <th className="pb-3 text-sm font-medium text-gray-500 dark:text-gray-400">Summary</th>
                </tr>
              </thead>
              <tbody>
                {agentDetail.recentRuns.map((run) => (
                  <Link
                    key={run.id}
                    to={`/runs/${run.id}`}
                    className="table-row hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                  >
                    <td className="py-3 text-sm text-gray-900 dark:text-white">
                      {new Date(run.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3 text-sm text-gray-600 dark:text-gray-400">
                      {run.runType}
                    </td>
                    <td className="py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        run.outcome === 'TRADED'
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                          : run.outcome === 'IN_PROGRESS'
                          ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400'
                          : 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'
                      }`}>
                        {run.outcome}
                      </span>
                    </td>
                    <td className="py-3 text-sm text-gray-900 dark:text-white">
                      {run.tradeCount}
                    </td>
                    <td className="py-3 text-sm text-gray-600 dark:text-gray-400">
                      {run.summary || '-'}
                    </td>
                  </Link>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 dark:text-gray-400">No recent runs</p>
        )}
      </div>
    </div>
  );
};

export default AgentDetailPage;
