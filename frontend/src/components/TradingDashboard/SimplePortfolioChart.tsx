import React from 'react';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts';
import { usePortfolioHistory } from '../../hooks';

interface SimplePortfolioChartProps {
  agentId: number;
}

const SimplePortfolioChart: React.FC<SimplePortfolioChartProps> = ({ agentId }) => {
  const { data: historyData, isLoading, error } = usePortfolioHistory(agentId, 7);

  // Custom tooltip formatter
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const value = payload[0].value;
      const time = new Date(label).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
      
      return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg p-2 shadow-lg">
          <p className="text-sm text-gray-600 dark:text-gray-300">{time}</p>
          <p className="text-sm font-semibold text-gray-900 dark:text-white">
            ${value?.toLocaleString() || '0'}
          </p>
        </div>
      );
    }
    return null;
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="h-[120px] flex items-center justify-center">
        <div className="animate-pulse flex space-x-1">
          <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce"></div>
          <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
          <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="h-[120px] flex items-center justify-center">
        <div className="text-xs text-gray-400 text-center">
          <div className="mb-1">📊</div>
          <div>Chart unavailable</div>
        </div>
      </div>
    );
  }

  // No data state
  if (!historyData || historyData.length === 0) {
    return (
      <div className="h-[120px] flex items-center justify-center">
        <div className="text-xs text-gray-400 text-center">
          <div className="mb-1">📈</div>
          <div>No history data</div>
          <div className="text-xs mt-1">Charts will appear after trading</div>
        </div>
      </div>
    );
  }

  // Determine line color based on performance
  const firstValue = historyData[0]?.portfolioValue || 0;
  const lastValue = historyData[historyData.length - 1]?.portfolioValue || 0;
  const isPositive = lastValue >= firstValue;
  const lineColor = isPositive ? '#10b981' : '#ef4444'; // green-500 : red-500

  return (
    <div className="h-[120px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={historyData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
          <XAxis 
            dataKey="timestamp"
            hide
          />
          <YAxis 
            hide
            domain={['dataMin - 100', 'dataMax + 100']}
          />
          <Tooltip 
            content={<CustomTooltip />}
            cursor={{ stroke: '#e5e7eb', strokeWidth: 1 }}
          />
          <Line
            type="monotone"
            dataKey="portfolioValue"
            stroke={lineColor}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 3, fill: lineColor }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default SimplePortfolioChart;