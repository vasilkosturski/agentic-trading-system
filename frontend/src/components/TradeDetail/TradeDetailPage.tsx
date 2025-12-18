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
          <i className="pi pi-spin pi-spinner text-4xl text-blue-600 dark:text-blue-400"></i>
          <p className="text-gray-500 dark:text-gray-400 mt-3">Loading trade details...</p>
        </div>
      </div>
    );
  }

  if (error || !tradeDetail) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 text-center">
          <i className="pi pi-exclamation-triangle text-5xl text-red-500 dark:text-red-400 mb-4"></i>
          <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-2">Trade Not Found</h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6">The requested trade could not be found.</p>
          <button
            onClick={() => navigate('/')}
            className="bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 text-white font-medium px-6 py-2 rounded-lg transition-colors"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const { trade, summary, fullReasoning, researchSources, historicalContext, relatedTrades, runId, runSummary, reasoningSteps } = tradeDetail;

  // Parse JSON strings if available
  let parsedSources: any[] = [];
  let parsedResearchSummary: string | null = null;
  let parsedHistoricalInsights: any[] = [];
  let parsedAgentContext: any = null;

  try {
    if (researchSources) {
      const parsed = JSON.parse(researchSources);
      // Extract both summary and sources from {summary, sources} structure
      parsedResearchSummary = parsed.summary || null;
      parsedSources = parsed.sources || [];
    }
    if (historicalContext) {
      const parsed = JSON.parse(historicalContext);
      // Extract insights array from {summary, insights} structure
      parsedHistoricalInsights = parsed.insights || [];
      // Extract agent context (portfolio state) from historical context
      parsedAgentContext = parsed.agentContext || null;
    }
  } catch (e) {
    console.error('Failed to parse JSON fields:', e);
  }

  /**
   * Helper to extract summary from JSON string if present.
   * Sometimes reasoningText contains stringified JSON like: '{"summary": "...", "sources": [...]}'
   */
  const extractSummaryFromJson = (text: string): string | null => {
    if (!text) return null;

    // Check if text looks like JSON (starts with { or contains "summary":)
    const trimmed = text.trim();
    if (trimmed.startsWith('{') || trimmed.includes('"summary"')) {
      try {
        const parsed = JSON.parse(trimmed);
        if (parsed.summary && typeof parsed.summary === 'string') {
          return parsed.summary;
        }
      } catch (e) {
        // Not valid JSON, continue with original text
      }
    }

    return null;
  };

  /**
   * Parse reasoning text to extract structured data context and sources.
   * The reasoning text contains special markers:
   * - "📊 Data Context:" for historical database access
   * - "🌐 Market Research:" for web research
   * - "  • " for source citations
   */
  const parseReasoningText = (text: string) => {
    if (!text) return { cleanText: '', dataContext: [], sources: [] };

    // First check if the text is a JSON string with a summary
    const jsonSummary = extractSummaryFromJson(text);
    if (jsonSummary) {
      return { cleanText: jsonSummary, dataContext: [], sources: [] };
    }

    const lines = text.split('\n');
    let cleanText = '';
    const dataContext: string[] = [];
    const sources: any[] = [];
    let currentSection: 'clean' | 'data' | 'research' | 'sources' = 'clean';

    for (const line of lines) {
      const trimmed = line.trim();

      if (trimmed.startsWith('📊 Data Context:')) {
        currentSection = 'data';
        continue;
      } else if (trimmed.startsWith('🌐 Market Research:')) {
        currentSection = 'research';
        continue;
      } else if (trimmed === 'Sources:') {
        currentSection = 'sources';
        continue;
      }

      if (currentSection === 'data' && trimmed && !trimmed.startsWith('🌐')) {
        dataContext.push(trimmed);
      } else if (currentSection === 'sources' && trimmed.startsWith('•')) {
        // Parse source: "• Title - URL"
        const sourceText = trimmed.substring(1).trim();
        const dashIndex = sourceText.lastIndexOf(' - ');
        if (dashIndex > 0) {
          const title = sourceText.substring(0, dashIndex).trim();
          const url = sourceText.substring(dashIndex + 3).trim();
          sources.push({ title, url });
        }
      } else if (currentSection === 'clean') {
        cleanText += line + '\n';
      } else if (currentSection === 'research' && trimmed && !trimmed.startsWith('Sources:')) {
        cleanText += line + '\n';
      }
    }

    return { cleanText: cleanText.trim(), dataContext, sources };
  };

  /**
   * Build enhanced reasoning steps from backend data.
   * Uses actual reasoning steps from the run, enriched with parsed data sources.
   */
  const buildEnhancedSteps = () => {
    if (!reasoningSteps || reasoningSteps.length === 0) {
      // Fallback: build basic steps if no reasoning data
      return [{
        id: 1,
        stepType: 'decision',
        stepDescription: `Decided: ${trade.type} ${trade.quantity} shares of ${trade.symbol}`,
        reasoningText: summary || fullReasoning || 'Investment decision based on analysis.',
        timestamp: trade.timestamp,
        sequenceNumber: 1
      }];
    }

    // Use actual reasoning steps from backend, parse and enhance them
    return reasoningSteps.map((step: any) => {
      const { cleanText, dataContext, sources } = parseReasoningText(step.reasoningText);

      // For research steps, use the parsed research summary as the reasoning text
      let displayText = cleanText || step.reasoningText;
      if (step.stepType === 'research' && parsedResearchSummary) {
        displayText = parsedResearchSummary;
      }

      // For research steps, inject both web sources and historical insights
      const stepSources = step.stepType === 'research' && parsedSources.length > 0
        ? parsedSources
        : (sources.length > 0 ? sources : undefined);

      const stepHistoricalInsights = step.stepType === 'research' && parsedHistoricalInsights.length > 0
        ? parsedHistoricalInsights
        : undefined;

      if (step.stepType === 'research') {
        console.log('[DEBUG] Research step data:', {
          stepType: step.stepType,
          parsedSourcesCount: parsedSources.length,
          textSourcesCount: sources.length,
          historicalInsightsCount: parsedHistoricalInsights.length,
          hasParsedSummary: !!parsedResearchSummary,
          finalSources: stepSources,
          finalInsights: stepHistoricalInsights
        });
      }

      return {
        id: step.id,
        stepType: step.stepType,
        stepDescription: step.stepDescription,
        reasoningText: displayText,
        timestamp: step.timestamp,
        sequenceNumber: step.sequenceNumber,
        sources: stepSources,
        dataContext: dataContext.length > 0 ? dataContext : undefined,
        historicalInsights: stepHistoricalInsights
      };
    });
  };

  const enhancedSteps = buildEnhancedSteps();

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Back Button */}
      <button
        onClick={() => navigate('/')}
        className="mb-6 flex items-center space-x-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
      >
        <i className="pi pi-arrow-left"></i>
        <span>Back to Dashboard</span>
      </button>

      {/* Trade Summary Header */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center space-x-3 mb-2">
              <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-lg font-bold">
                {trade.agentName.charAt(0)}
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{trade.agentName}'s Trade</h1>
                <p className="text-gray-500 dark:text-gray-400 text-sm">{formatTimestamp(trade.timestamp)}</p>
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
          <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Symbol</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{trade.symbol}</p>
          </div>
          <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Quantity</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{trade.quantity}</p>
          </div>
          <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Price per Share</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{formatPrice(trade.price)}</p>
          </div>
          <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Total Value</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{formatPrice(trade.totalValue)}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Agent Reasoning Timeline with integrated research sources */}
          <AgentReasoningTimeline
            reasoningSteps={enhancedSteps}
            fallbackReasoning={fullReasoning}
          />

          {/* Related Trades */}
          {relatedTrades && relatedTrades.length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center">
                <i className="pi pi-history text-blue-600 dark:text-blue-400 mr-2"></i>
                Related Trades in {trade.symbol}
              </h2>
              <div className="space-y-2">
                {relatedTrades.map((relatedTrade) => (
                  <div
                    key={relatedTrade.id}
                    onClick={() => navigate(`/trades/${relatedTrade.id}`)}
                    className="flex items-center justify-between p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center space-x-3">
                      <Tag
                        value={relatedTrade.type}
                        severity={relatedTrade.type === 'BUY' ? 'success' : 'danger'}
                        className="text-xs"
                      />
                      <span className="font-medium text-gray-900 dark:text-white">{relatedTrade.quantity} shares</span>
                      <span className="text-gray-600 dark:text-gray-400">at {formatPrice(relatedTrade.price)}</span>
                    </div>
                    <span className="text-sm text-gray-500 dark:text-gray-400">{formatTimestamp(relatedTrade.timestamp)}</span>
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
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center">
                <i className="pi pi-bolt text-blue-600 dark:text-blue-400 mr-2"></i>
                Part of Run
              </h2>
              <div
                onClick={() => navigate(`/runs/${runId}`)}
                className="border-2 border-blue-200 dark:border-blue-800 rounded-lg p-4 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-400 dark:hover:border-blue-600 cursor-pointer transition-all"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Run ID</span>
                  <span className="font-mono text-lg font-bold text-blue-600 dark:text-blue-400">#{runId}</span>
                </div>
                {runSummary && (
                  <p className="text-sm text-gray-700 dark:text-gray-300 mt-2 line-clamp-2">
                    {runSummary}
                  </p>
                )}
                <div className="flex items-center justify-end mt-3 text-blue-600 dark:text-blue-400">
                  <span className="text-sm font-medium">View run details</span>
                  <i className="pi pi-arrow-right ml-2 text-xs"></i>
                </div>
              </div>
            </div>
          )}

          {/* Agent Context */}
          {parsedAgentContext && (
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center">
                <i className="pi pi-chart-line text-blue-600 dark:text-blue-400 mr-2"></i>
                Agent Context
              </h2>
              <div className="space-y-3">
                {parsedAgentContext.portfolioValueBefore && (
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Portfolio Value</p>
                    <p className="text-lg font-bold text-gray-900 dark:text-white">{formatPrice(parsedAgentContext.portfolioValueBefore)}</p>
                  </div>
                )}
                {parsedAgentContext.cashBefore && (
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Cash Available</p>
                    <p className="text-lg font-bold text-gray-900 dark:text-white">{formatPrice(parsedAgentContext.cashBefore)}</p>
                  </div>
                )}
                {parsedAgentContext.positionsBefore !== undefined && (
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Positions</p>
                    <p className="text-lg font-bold text-gray-900 dark:text-white">{parsedAgentContext.positionsBefore}</p>
                  </div>
                )}
                {parsedAgentContext.recentPerformancePct !== undefined && (
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Recent Performance</p>
                    <p className={`text-lg font-bold ${parsedAgentContext.recentPerformancePct >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                      {parsedAgentContext.recentPerformancePct.toFixed(2)}%
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Trade Info */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Trade Information</h2>
            <div className="space-y-3 text-sm">
              <div>
                <p className="text-gray-600 dark:text-gray-400">Trade ID</p>
                <p className="font-mono text-gray-900 dark:text-white">#{trade.id}</p>
              </div>
              <div>
                <p className="text-gray-600 dark:text-gray-400">Timestamp</p>
                <p className="text-gray-900 dark:text-white">{formatTimestamp(trade.timestamp)}</p>
              </div>
              <div>
                <p className="text-gray-600 dark:text-gray-400">Agent</p>
                <p className="text-gray-900 dark:text-white">{trade.agentName}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TradeDetailPage;
