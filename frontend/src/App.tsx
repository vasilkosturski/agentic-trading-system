import { Routes, Route } from 'react-router-dom'
import TradingDashboard from './components/TradingDashboard/TradingDashboard'
import TradeDetailPage from './components/TradeDetail/TradeDetailPage'
import AgentDetailPage from './components/AgentDetailPage'

function App() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Agentic Trading System
              </h1>
              <span className="ml-3 px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded-full">
                v1.0.0
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm text-gray-600 dark:text-gray-300">Live</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Routes>
          <Route path="/" element={<TradingDashboard />} />
          <Route path="/dashboard" element={<TradingDashboard />} />
          <Route path="/agents/:agentName" element={<AgentDetailPage />} />
          <Route path="/trades/:tradeId" element={<TradeDetailPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App