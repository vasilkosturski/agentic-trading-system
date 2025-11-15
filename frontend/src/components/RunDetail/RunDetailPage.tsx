import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { runService, type RunDetail } from '../../services/runService';

const RunDetailPage = () => {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();

  const { data: runDetail, isLoading, error } = useQuery<RunDetail>({
    queryKey: ['runDetail', runId],
    queryFn: () => runService.getRunDetail(Number(runId)),
    enabled: !!runId,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !runDetail) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <p className="text-red-600 dark:text-red-400">
            Failed to load run details. Run not found or server error.
          </p>
          <button
            onClick={() => navigate(-1)}
            className="text-blue-600 hover:underline mt-4 inline-block"
          >
            ← Go Back
          </button>
        </div>
      </div>
    );
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  // Parse research sources if available
  let researchSources: any[] = [];
  if (runDetail.researchSources) {
    try {
      researchSources = JSON.parse(runDetail.researchSources);
    } catch (e) {
      console.error('Failed to parse research sources:', e);
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Back Button */}
      <button
        onClick={() => {
          if (runDetail.agentId) {
            navigate(`/agents/${runDetail.agentId}`);
          } else {
            navigate(-1);
          }
        }}
        className="text-blue-600 hover:underline mb-4 inline-block"
      >
        ← Back to {runDetail.agentName}
      </button>

      {/* Run Header */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Run #{runDetail.id}
          </h1>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            runDetail.outcome === 'TRADED'
              ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
              : runDetail.outcome === 'NO_TRADE'
              ? 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'
              : runDetail.outcome === 'ERROR'
              ? 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
              : 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400'
          }`}>
            {runDetail.outcome}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="text-gray-500 dark:text-gray-400">Agent</div>
            <div className="font-semibold text-gray-900 dark:text-white">
              {runDetail.agentName}
            </div>
          </div>
          <div>
            <div className="text-gray-500 dark:text-gray-400">Type</div>
            <div className="font-semibold text-gray-900 dark:text-white">
              {runDetail.runType}
            </div>
          </div>
          <div>
            <div className="text-gray-500 dark:text-gray-400">Duration</div>
            <div className="font-semibold text-gray-900 dark:text-white">
              {formatDuration(runDetail.durationSeconds)}
            </div>
          </div>
          <div>
            <div className="text-gray-500 dark:text-gray-400">Trades</div>
            <div className="font-semibold text-gray-900 dark:text-white">
              {runDetail.tradeCount}
            </div>
          </div>
        </div>

        <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
          <div>Started: {new Date(runDetail.startTime).toLocaleString()}</div>
          {runDetail.endTime && (
            <div>Ended: {new Date(runDetail.endTime).toLocaleString()}</div>
          )}
        </div>
      </div>

      {/* Error Message (if any) */}
      {runDetail.errorMessage && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold text-red-800 dark:text-red-400 mb-2">
            Error
          </h2>
          <p className="text-red-600 dark:text-red-400 whitespace-pre-wrap">
            {runDetail.errorMessage}
          </p>
        </div>
      )}

      {/* Summary */}
      {runDetail.summary && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
            Summary
          </h2>
          <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
            {runDetail.summary}
          </p>
        </div>
      )}

      {/* Agent Reasoning Timeline */}
      {runDetail.reasoningSteps && runDetail.reasoningSteps.length > 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            Agent Reasoning Timeline
          </h2>
          <div className="space-y-4">
            {runDetail.reasoningSteps.map((step, index) => {
              // Define colors and icons for each step type
              const stepConfig = {
                initialization: { 
                  iconBg: 'bg-blue-100 dark:bg-blue-900/20',
                  badgeBg: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400',
                  icon: '🚀',
                  label: 'Initialization' 
                },
                research: { 
                  iconBg: 'bg-purple-100 dark:bg-purple-900/20',
                  badgeBg: 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400',
                  icon: '🔍',
                  label: 'Research' 
                },
                analysis: { 
                  iconBg: 'bg-yellow-100 dark:bg-yellow-900/20',
                  badgeBg: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400',
                  icon: '📊',
                  label: 'Analysis' 
                },
                decision: { 
                  iconBg: 'bg-green-100 dark:bg-green-900/20',
                  badgeBg: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400',
                  icon: '💡',
                  label: 'Decision' 
                },
                execution: { 
                  iconBg: 'bg-indigo-100 dark:bg-indigo-900/20',
                  badgeBg: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/20 dark:text-indigo-400',
                  icon: '⚡',
                  label: 'Execution' 
                },
              }[step.stepType] || { 
                iconBg: 'bg-gray-100 dark:bg-gray-900/20',
                badgeBg: 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400',
                icon: '•',
                label: step.stepType 
              };

              return (
                <div key={step.id} className="flex gap-4">
                  {/* Timeline line */}
                  <div className="flex flex-col items-center">
                    <div className={`w-10 h-10 rounded-full ${stepConfig.iconBg} flex items-center justify-center text-lg`}>
                      {stepConfig.icon}
                    </div>
                    {index < runDetail.reasoningSteps!.length - 1 && (
                      <div className="w-0.5 h-full bg-gray-200 dark:bg-gray-700 mt-2"></div>
                    )}
                  </div>
                  
                  {/* Step content */}
                  <div className="flex-1 pb-6">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${stepConfig.badgeBg}`}>
                        {stepConfig.label}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {new Date(step.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                      {step.stepDescription}
                    </h3>
                    <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                      {step.reasoningText}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : runDetail.fullReasoning && (
        // Fallback to old full reasoning if no reasoning steps available
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
            Full Reasoning
          </h2>
          <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
            {runDetail.fullReasoning}
          </p>
        </div>
      )}

      {/* Research Sources */}
      {researchSources.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
            Research Sources
          </h2>
          <div className="space-y-3">
            {researchSources.map((source, index) => (
              <div key={index} className="border-l-4 border-blue-500 pl-4 py-2">
                {source.url ? (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline font-medium"
                  >
                    {source.title || source.url}
                  </a>
                ) : (
                  <div className="font-medium text-gray-900 dark:text-white">
                    {source.title || 'Untitled Source'}
                  </div>
                )}
                {source.snippet && (
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {source.snippet}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trades Section */}
      {runDetail.trades && runDetail.trades.length > 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            Trades Executed ({runDetail.trades.length})
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-gray-200 dark:border-gray-700">
                <tr className="text-left">
                  <th className="pb-3 text-sm font-medium text-gray-500 dark:text-gray-400">
                    Time
                  </th>
                  <th className="pb-3 text-sm font-medium text-gray-500 dark:text-gray-400">
                    Type
                  </th>
                  <th className="pb-3 text-sm font-medium text-gray-500 dark:text-gray-400">
                    Symbol
                  </th>
                  <th className="pb-3 text-sm font-medium text-gray-500 dark:text-gray-400">
                    Qty
                  </th>
                  <th className="pb-3 text-sm font-medium text-gray-500 dark:text-gray-400">
                    Price
                  </th>
                  <th className="pb-3 text-sm font-medium text-gray-500 dark:text-gray-400">
                    Total
                  </th>
                  <th className="pb-3 text-sm font-medium text-gray-500 dark:text-gray-400">
                    Rationale
                  </th>
                </tr>
              </thead>
              <tbody>
                {runDetail.trades.map((trade) => (
                  <Link
                    key={trade.id}
                    to={`/trades/${trade.id}`}
                    className="table-row hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                  >
                    <td className="py-3 text-sm text-gray-900 dark:text-white">
                      {new Date(trade.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        trade.transactionType === 'BUY'
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                          : 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
                      }`}>
                        {trade.transactionType}
                      </span>
                    </td>
                    <td className="py-3 text-sm font-semibold text-gray-900 dark:text-white">
                      {trade.symbol}
                    </td>
                    <td className="py-3 text-sm text-gray-900 dark:text-white">
                      {Math.abs(trade.quantity)}
                    </td>
                    <td className="py-3 text-sm text-gray-900 dark:text-white">
                      {formatCurrency(trade.price)}
                    </td>
                    <td className="py-3 text-sm font-semibold text-gray-900 dark:text-white">
                      {formatCurrency(trade.totalAmount)}
                    </td>
                    <td className="py-3 text-sm text-gray-600 dark:text-gray-400">
                      {trade.rationale || '-'}
                    </td>
                  </Link>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : runDetail.outcome === 'NO_TRADE' && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            No Trades
          </h2>
          <p className="text-gray-700 dark:text-gray-300">
            The agent decided not to execute any trades during this run.
            {runDetail.fullReasoning && (
              <span> See the "Full Reasoning" section above for details.</span>
            )}
          </p>
        </div>
      )}
    </div>
  );
};

export default RunDetailPage;
