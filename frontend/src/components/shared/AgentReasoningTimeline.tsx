import React from 'react';

export interface ResearchSource {
  title: string;
  url: string;
  snippet?: string;
}

export interface ReasoningStep {
  id: number;
  stepType: string;
  stepDescription: string;
  reasoningText: string;
  timestamp: string;
  sequenceNumber: number;
  sources?: ResearchSource[];
  dataContext?: string[]; // Historical data accessed (portfolio, trading history, etc.)
}

interface AgentReasoningTimelineProps {
  reasoningSteps?: ReasoningStep[];
  fallbackReasoning?: string;
}

const AgentReasoningTimeline: React.FC<AgentReasoningTimelineProps> = ({ 
  reasoningSteps, 
  fallbackReasoning 
}) => {
  const hasSteps = reasoningSteps && reasoningSteps.length > 0;
  const hasReasoning = fallbackReasoning && fallbackReasoning.trim().length > 0;

  if (!hasSteps && !hasReasoning) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Timeline Section */}
      {hasSteps && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            Reasoning Timeline
          </h2>
          <div className="space-y-4">
            {reasoningSteps!.map((step, index) => {
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
                    {index < reasoningSteps!.length - 1 && (
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

                    {/* Historical data context if present */}
                    {step.dataContext && step.dataContext.length > 0 && (
                      <div className="mt-3 space-y-2">
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 flex items-center">
                          <i className="pi pi-database mr-1.5 text-[10px]"></i>
                          Historical Data Accessed:
                        </p>
                        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-md p-3 space-y-1.5">
                          {step.dataContext.map((item, idx) => (
                            <div key={idx} className="text-xs text-gray-700 dark:text-gray-300 flex items-start">
                              <span className="text-blue-600 dark:text-blue-400 mr-2">•</span>
                              <span>{item}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Research sources if present */}
                    {step.sources && step.sources.length > 0 && (
                      <div className="mt-3 space-y-2">
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 flex items-center">
                          <i className="pi pi-globe mr-1.5 text-[10px]"></i>
                          Web Research Sources ({step.sources.length}):
                        </p>
                        <div className="space-y-1.5">
                          {step.sources.map((source, idx) => (
                            <div key={idx} className="bg-gray-50 dark:bg-gray-900/50 rounded-md p-2.5 hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors">
                              <a
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium flex items-center"
                              >
                                {source.title}
                                <i className="pi pi-external-link ml-1.5 text-[10px]"></i>
                              </a>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Fallback section - only show if no steps available */}
      {!hasSteps && hasReasoning && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
            Trade Reasoning
          </h2>
          <div className="prose prose-sm max-w-none">
            <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
              {fallbackReasoning}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentReasoningTimeline;


