import React, { useEffect, useState } from 'react';
import { Card } from 'primereact/card';
import { ProgressBar } from 'primereact/progressbar';
import { Badge } from 'primereact/badge';
import { AgentStatusUpdate } from '../../services/webSocketService';
import './LiveAgentActivity.css';

interface LiveAgentActivityProps {
  agentStatuses: Map<number, AgentStatusUpdate>;
  isRunning: boolean;
}

const phaseConfig: Record<string, { icon: string; color: string; label: string }> = {
  INITIALIZING: { icon: '🔄', color: 'bg-blue-500', label: 'Initializing' },
  RESEARCHING: { icon: '🔍', color: 'bg-cyan-500', label: 'Researching & Analyzing' },
  DECIDING: { icon: '💭', color: 'bg-yellow-500', label: 'Making Decision' },
  TRADING: { icon: '💰', color: 'bg-green-500', label: 'Executing Trade' },
  COMPLETED: { icon: '✅', color: 'bg-gray-500', label: 'Completed' },
  ERROR: { icon: '❌', color: 'bg-red-500', label: 'Error' },
};

const AgentCard: React.FC<{ status: AgentStatusUpdate }> = ({ status }) => {
  const phase = phaseConfig[status.phase] || phaseConfig.INITIALIZING;
  const isComplete = status.phase === 'COMPLETED';
  const isError = status.phase === 'ERROR';

  return (
    <Card className="agent-status-card mb-3">
      <div className="flex items-start gap-3">
        <div className={`text-3xl ${isComplete || isError ? 'animate-none' : 'animate-pulse'}`}>
          {phase.icon}
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-bold m-0">{status.agentName}</h3>
            <Badge 
              value={status.progress + '%'} 
              severity={isComplete ? 'success' : isError ? 'danger' : 'info'}
            />
          </div>
          
          <div className="mb-2">
            <span className={`inline-block px-2 py-1 rounded text-xs font-semibold text-white ${phase.color}`}>
              {phase.label}
            </span>
          </div>
          
          <p className="text-sm text-gray-600 mb-2">{status.message}</p>
          
          <ProgressBar 
            value={status.progress} 
            showValue={false}
            className="h-2"
            color={isComplete ? '#22c55e' : isError ? '#ef4444' : undefined}
          />
          
          {status.outcome && (
            <div className="mt-2 p-2 bg-gray-100 rounded text-sm">
              <strong>Result:</strong> {status.outcome}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};

export const LiveAgentActivity: React.FC<LiveAgentActivityProps> = ({ agentStatuses, isRunning }) => {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (isRunning && agentStatuses.size > 0) {
      setVisible(true);
    } else if (!isRunning && agentStatuses.size === 0) {
      // Hide after a short delay when all agents complete
      const timer = setTimeout(() => setVisible(false), 5000);
      return () => clearTimeout(timer);
    }
  }, [isRunning, agentStatuses.size]);

  if (!visible && agentStatuses.size === 0) {
    return null;
  }

  return (
    <div className="live-agent-activity mb-4">
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold m-0 flex items-center gap-2">
            <span className="animate-pulse">🤖</span> Live Agent Activity
          </h2>
          {isRunning && (
            <Badge value="Running" severity="info" className="animate-pulse" />
          )}
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Array.from(agentStatuses.values()).map((status) => (
            <AgentCard key={status.agentId} status={status} />
          ))}
        </div>
        
        {agentStatuses.size === 0 && (
          <div className="text-center text-gray-500 py-4">
            Waiting for agents to start...
          </div>
        )}
      </Card>
    </div>
  );
};

