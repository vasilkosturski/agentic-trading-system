import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { tradesService } from '../../services/tradesService';
import { Tag } from 'primereact/tag';
import AgentReasoningTimeline from '../shared/AgentReasoningTimeline';

const TradeDetailPage: React.FC = () => {
  const { tradeId } = useParams<{ tradeId: string }>();
  const navigate = useNavigate();

  const { data: tradeDetail, isLoading, error } = useQuery({
    queryKey: ['tradeDetail', tradeId],
    queryFn: () => tradesService.getTradeDetail(Number(tradeId)),
    enabled: !!tradeId
  });

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatPrice = (price: number) => {
    return `$${price.toFixed(2)}`;
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-12">
          <i className="pi pi-spin pi-spinner text-4xl text-blue-600"></i>
          <p className="text-gray-500 mt-3">Loading trade details...</p>
        </div>
      </div>
    );
  }

  if (error || !tradeDetail) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-lg p-8 text-center">
          <i className="pi pi-exclamation-triangle text-5xl text-red-500 mb-4"></i>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Trade Not Found</h2>
          <p className="text-gray-600 mb-6">The requested trade could not be found.</p>
          <button
            onClick={() => navigate('/')}
            className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-6 py-2 rounded-lg transition-colors"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const { trade, fullReasoning, researchSources, agentContext, relatedTrades, runId, runSummary, reasoningSteps } = tradeDetail;

  // Parse JSON strings if available
  let parsedSources: any[] = [];
  let parsedContext: any = null;

  try {
    if (researchSources) parsedSources = JSON.parse(researchSources);
  } catch (e) {
    console.error('Failed to parse research sources:', e);
  }

  try {
    if (agentContext) parsedContext = JSON.parse(agentContext);
  } catch (e) {
    console.error('Failed to parse agent context:', e);
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Back Button */}
      <button
        onClick={() => navigate('/')}
        className="mb-6 flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
      >
        <i className="pi pi-arrow-left"></i>
        <span>Back to Dashboard</span>
      </button>

      {/* Trade Summary Header */}
      <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center space-x-3 mb-2">
              <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-lg font-bold">
                {trade.agentName.charAt(0)}
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{trade.agentName}'s Trade</h1>
                <p className="text-gray-500 text-sm">{formatTimestamp(trade.timestamp)}</p>
              </div>
            </div>
          </div>
          <Tag
            value={trade.type}
            severity={trade.type === 'BUY' ? 'success' : 'danger'}
            className="text-lg font-bold px-4 py-2"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
          <div className="bg-gray-50 p-4 rounded-lg">
            <p className="text-sm text-gray-600 mb-1">Symbol</p>
            <p className="text-2xl font-bold text-gray-900">{trade.symbol}</p>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <p className="text-sm text-gray-600 mb-1">Quantity</p>
            <p className="text-2xl font-bold text-gray-900">{trade.quantity}</p>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <p className="text-sm text-gray-600 mb-1">Price per Share</p>
            <p className="text-2xl font-bold text-gray-900">{formatPrice(trade.price)}</p>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <p className="text-sm text-gray-600 mb-1">Total Value</p>
            <p className="text-2xl font-bold text-gray-900">{formatPrice(trade.totalValue)}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Agent Reasoning Timeline */}
          <AgentReasoningTimeline
            reasoningSteps={reasoningSteps}
            fallbackReasoning={fullReasoning || trade.rationale}
          />

          {/* Research Sources */}
          {parsedSources.length > 0 && (
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                <i className="pi pi-book text-blue-600 mr-2"></i>
                Research Sources
              </h2>
              <div className="space-y-3">
                {parsedSources.map((source: any, index: number) => (
                  <div key={index} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
                    <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 font-medium flex items-center">
                      {source.title}
                      <i className="pi pi-external-link ml-2 text-sm"></i>
                    </a>
                    {source.snippet && <p className="text-sm text-gray-600 mt-2">{source.snippet}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Related Trades */}
          {relatedTrades && relatedTrades.length > 0 && (
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                <i className="pi pi-history text-blue-600 mr-2"></i>
                Related Trades in {trade.symbol}
              </h2>
              <div className="space-y-2">
                {relatedTrades.map((relatedTrade) => (
                  <div
                    key={relatedTrade.id}
                    onClick={() => navigate(`/trades/${relatedTrade.id}`)}
                    className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center space-x-3">
                      <Tag
                        value={relatedTrade.type}
                        severity={relatedTrade.type === 'BUY' ? 'success' : 'danger'}
                        className="text-xs"
                      />
                      <span className="font-medium">{relatedTrade.quantity} shares</span>
                      <span className="text-gray-600">at {formatPrice(relatedTrade.price)}</span>
                    </div>
                    <span className="text-sm text-gray-500">{formatTimestamp(relatedTrade.timestamp)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Run Link Section */}
          {runId && (
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                <i className="pi pi-bolt text-blue-600 mr-2"></i>
                Part of Run
              </h2>
              <div
                onClick={() => navigate(`/runs/${runId}`)}
                className="border-2 border-blue-200 rounded-lg p-4 hover:bg-blue-50 hover:border-blue-400 cursor-pointer transition-all"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">Run ID</span>
                  <span className="font-mono text-lg font-bold text-blue-600">#{runId}</span>
                </div>
                {runSummary && (
                  <p className="text-sm text-gray-700 mt-2 line-clamp-2">
                    {runSummary}
                  </p>
                )}
                <div className="flex items-center justify-end mt-3 text-blue-600">
                  <span className="text-sm font-medium">View run details</span>
                  <i className="pi pi-arrow-right ml-2 text-xs"></i>
                </div>
              </div>
            </div>
          )}

          {/* Agent Context */}
          {parsedContext && (
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                <i className="pi pi-chart-line text-blue-600 mr-2"></i>
                Agent Context
              </h2>
              <div className="space-y-3">
                {parsedContext.portfolioValueBefore && (
                  <div>
                    <p className="text-sm text-gray-600">Portfolio Value</p>
                    <p className="text-lg font-bold text-gray-900">{formatPrice(parsedContext.portfolioValueBefore)}</p>
                  </div>
                )}
                {parsedContext.cashBefore && (
                  <div>
                    <p className="text-sm text-gray-600">Cash Available</p>
                    <p className="text-lg font-bold text-gray-900">{formatPrice(parsedContext.cashBefore)}</p>
                  </div>
                )}
                {parsedContext.positionsBefore !== undefined && (
                  <div>
                    <p className="text-sm text-gray-600">Positions</p>
                    <p className="text-lg font-bold text-gray-900">{parsedContext.positionsBefore}</p>
                  </div>
                )}
                {parsedContext.recentPerformancePct !== undefined && (
                  <div>
                    <p className="text-sm text-gray-600">Recent Performance</p>
                    <p className={`text-lg font-bold ${parsedContext.recentPerformancePct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {parsedContext.recentPerformancePct.toFixed(2)}%
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Trade Info */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Trade Information</h2>
            <div className="space-y-3 text-sm">
              <div>
                <p className="text-gray-600">Trade ID</p>
                <p className="font-mono text-gray-900">#{trade.id}</p>
              </div>
              <div>
                <p className="text-gray-600">Timestamp</p>
                <p className="text-gray-900">{formatTimestamp(trade.timestamp)}</p>
              </div>
              <div>
                <p className="text-gray-600">Agent</p>
                <p className="text-gray-900">{trade.agentName}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TradeDetailPage;
