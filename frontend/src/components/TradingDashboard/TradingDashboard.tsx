import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useTradingAgents } from '../../hooks';
import SimplePortfolioChart from './SimplePortfolioChart';
import RecentTrades from './RecentTrades';
import { tradingService } from '../../services/tradingService';
import { Toast } from 'primereact/toast';
import { webSocketService, AgentStatusUpdate } from '../../services/webSocketService';
import { LiveAgentActivity } from '../LiveAgentActivity/LiveAgentActivity';

const TradingDashboard = () => {
  const { agents = [], isLoading, error, isError, refetch } = useTradingAgents();
  const [isTriggering, setIsTriggering] = useState(false);
  const [agentStatuses, setAgentStatuses] = useState<Map<number, AgentStatusUpdate>>(new Map());
  const [isCycleRunning, setIsCycleRunning] = useState(false);
  const toast = React.useRef<Toast>(null);

  // Connect to WebSocket on mount
  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_BASE_URL || '/api';
    webSocketService.connect(apiUrl);

    const unsubscribe = webSocketService.subscribe((update: AgentStatusUpdate) => {
      setAgentStatuses(prev => {
        const newMap = new Map(prev);
        newMap.set(update.agentId, update);
        return newMap;
      });

      // Detect cycle start (any agent starts = cycle is running)
      if (update.phase === 'INITIALIZING') {
        setIsCycleRunning(true);
      }

      // Check if all agents completed
      if (update.phase === 'COMPLETED' || update.phase === 'ERROR') {
        setAgentStatuses(current => {
          const allCompleted = Array.from(current.values()).every(
            s => s.phase === 'COMPLETED' || s.phase === 'ERROR'
          );
          if (allCompleted && current.size === 4) { // We have 4 agents
            setIsCycleRunning(false);
            // Refresh dashboard data after 2 seconds
            setTimeout(() => {
              refetch();
              setAgentStatuses(new Map()); // Clear statuses
            }, 2000);
          }
          return current;
        });
      }
    });

    return () => {
      unsubscribe();
      webSocketService.disconnect();
    };
  }, [refetch]);

  const formatTimeAgo = (minutes: number): string => {
    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;

    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;

    if (hours < 24) {
      return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m ago` : `${hours}h ago`;
    }

    const days = Math.floor(hours / 24);
    const remainingHours = hours % 24;

    return remainingHours > 0 ? `${days}d ${remainingHours}h ago` : `${days}d ago`;
  };

  const getActivityStatus = (lastActivity: string) => {
    const minutesAgo = Math.round((Date.now() - new Date(lastActivity).getTime()) / 60000);

    if (minutesAgo <= 5) {
      return {
        text: formatTimeAgo(minutesAgo),
        color: 'text-green-600 dark:text-green-400',
        dotColor: 'bg-green-500',
        tooltip: 'Active now'
      };
    }

    if (minutesAgo <= 120) { // Within 2 hours
      return {
        text: formatTimeAgo(minutesAgo),
        color: 'text-gray-600 dark:text-gray-400',
        dotColor: 'bg-gray-400',
        tooltip: 'Recently active'
      };
    }

    return {
      text: formatTimeAgo(minutesAgo),
      color: 'text-red-500 dark:text-red-400',
      dotColor: 'bg-red-500',
      tooltip: 'Inactive'
    };
  };

  const formatNextCycle = (lastActivity: string, cycleIntervalSeconds: number) => {
    if (!lastActivity || !cycleIntervalSeconds) {
      return { text: 'Unknown', color: 'text-gray-600 dark:text-gray-400', bg: 'bg-gray-100 dark:bg-gray-900/20' };
    }

    const lastActivityTime = new Date(lastActivity).getTime();
    const nextCycleTime = lastActivityTime + (cycleIntervalSeconds * 1000);
    const now = Date.now();
    const msUntilNext = nextCycleTime - now;
    const minutesUntilNext = Math.round(msUntilNext / 60000);
    const minutesSinceLastActivity = Math.round((now - lastActivityTime) / 60000);

    // If cycle is overdue by more than 2 minutes, show time since last activity
    if (minutesUntilNext < -2) {
      return {
        text: `Idle (${formatTimeAgo(minutesSinceLastActivity)} ago)`,
        color: 'text-gray-500 dark:text-gray-500',
        bg: 'bg-gray-100 dark:bg-gray-900/20'
      };
    }

    // If cycle time just passed (0-2 min overdue), show "Trading now..."
    if (minutesUntilNext <= 0) {
      return { text: 'Trading now...', color: 'text-green-600', bg: 'bg-green-100 dark:bg-green-900/20' };
    }

    if (minutesUntilNext === 1) {
      return { text: 'Next cycle in 1 min', color: 'text-green-600 dark:text-green-400', bg: 'bg-green-100 dark:bg-green-900/20' };
    }

    return { text: `Next cycle in ${minutesUntilNext} min`, color: 'text-gray-600 dark:text-gray-400', bg: 'bg-gray-100 dark:bg-gray-900/20' };
  };

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

  const handleTriggerCycle = async () => {
    setIsTriggering(true);
    
    try {
      await tradingService.triggerManualCycle();
      toast.current?.show({
        severity: 'success',
        summary: 'Trading Cycle Started',
        detail: 'Watch the agents work in real-time below',
        life: 3000,
      });
    } catch (error: any) {
      // Check for explicit reason field (proper API contract)
      const reason = error.reason;
      const message = error.message || 'Failed to trigger trading cycle';
      
      // Note: MARKET_CLOSED shouldn't happen in demo mode, but kept for safety
      toast.current?.show({
        severity: reason === 'MARKET_CLOSED' ? 'warn' : 'error',
        summary: reason === 'MARKET_CLOSED' ? 'Market Closed' : 'Error',
        detail: message,
        life: 5000,
      });
    } finally {
      setIsTriggering(false);
    }
  };

  return (
    <div className="space-y-6">
      <Toast ref={toast} />
      <div className="text-center py-8">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
          Trading Dashboard
        </h2>
        <div className="flex items-center justify-center space-x-4 mb-6">
          <p className="text-lg text-gray-600 dark:text-gray-300">
            {agents.length > 0
              ? `${agents.length} Autonomous Trader${agents.length !== 1 ? 's' : ''}: ${agents.map(a => a.agentName).join(', ')}`
              : 'Loading traders...'
            }
          </p>
        </div>

        {/* Manual Trading Cycle Button */}
        <div className="mb-8">
          <button
            onClick={handleTriggerCycle}
            disabled={isTriggering}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors flex items-center space-x-2 disabled:cursor-not-allowed mx-auto shadow-md hover:shadow-lg"
            title="Trigger a manual trading cycle for all agents (demo mode - runs 24/7 with end-of-day data)"
          >
            {isTriggering ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                <span>Running Trading Cycle...</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Run Trading Cycle for All Agents</span>
              </>
            )}
          </button>
        </div>

        {/* Live Agent Activity */}
        <LiveAgentActivity agentStatuses={agentStatuses} isRunning={isCycleRunning} />
        
        {/* 4-trader grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 max-w-7xl mx-auto">
          {agents.map((agent) => {
            const nextCycle = formatNextCycle(agent.lastActivity, agent.cycleIntervalSeconds ?? 3600);
            const activityStatus = getActivityStatus(agent.lastActivity);
            return (
            <Link key={agent.agentId} to={`/agents/${agent.agentId}`}>
            <div className="trading-card hover:shadow-xl hover:scale-[1.02] hover:border-blue-400 transition-all duration-200 cursor-pointer">
              <div className="flex items-center justify-between mb-4">
                <h3 className="trader-header">{agent.agentName}</h3>
                <div className={`flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium ${nextCycle.bg} ${nextCycle.color}`}>
                  <div className={`w-1.5 h-1.5 rounded-full ${
                    nextCycle.text === 'Trading now...' ? 'bg-green-500 animate-pulse' : 'bg-gray-500'
                  }`}></div>
                  <span>{nextCycle.text}</span>
                </div>
              </div>
              
              <div className="space-y-4">
                <div className="text-center">
                  <div className={`text-2xl font-bold ${
                    Math.abs(agent.totalReturnPercent ?? 0) < 0.01 ? 'text-gray-900 dark:text-white' :
                    (agent.totalReturnPercent ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {formatCurrency(agent.portfolioValue)}
                  </div>
                  <div className="text-sm text-gray-500 mb-2">
                    Portfolio Value
                  </div>
                  <div className={`text-sm font-medium ${
                    Math.abs(agent.dayPnL) < 0.01 ? 'text-gray-600 dark:text-gray-400' :
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
                      Math.abs(agent.totalReturnPercent ?? 0) < 0.01 ? 'text-gray-600 dark:text-gray-400' :
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
                  <SimplePortfolioChart agentId={agent.agentId} />
                </div>

                {/* Last Activity with Status Indicator */}
                <div className="flex items-center justify-center space-x-2 text-xs" title={activityStatus.tooltip}>
                  <div className={`w-2 h-2 rounded-full ${activityStatus.dotColor}`}></div>
                  <span className={`font-medium ${activityStatus.color}`}>
                    Last active {activityStatus.text}
                  </span>
                </div>
              </div>
            </div>
            </Link>
            );
          })}
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