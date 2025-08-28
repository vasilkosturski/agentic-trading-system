import React, { useState, useMemo } from 'react';
import { useRecentTrades } from '../../hooks/useRecentTrades';

const RecentTrades: React.FC = () => {
  const { trades, loading, error } = useRecentTrades(50);
  const [selectedAgent, setSelectedAgent] = useState<string>('all');
  const [sortField, setSortField] = useState<string>('timestamp');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const itemsPerPage = 10;

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatPrice = (price: number) => {
    return `$${price.toFixed(2)}`;
  };

  const formatTotal = (total: number) => {
    return `$${total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  // Get unique agent names for filter dropdown
  const uniqueAgents = useMemo(() => {
    const agents = [...new Set(trades.map(trade => trade.agentName))].sort();
    return agents;
  }, [trades]);

  // Filter and sort trades
  const processedTrades = useMemo(() => {
    let filtered = trades;
    
    // Apply agent filter
    if (selectedAgent !== 'all') {
      filtered = filtered.filter(trade => trade.agentName === selectedAgent);
    }
    
    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(trade =>
        trade.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
        trade.rationale.toLowerCase().includes(searchTerm.toLowerCase()) ||
        trade.agentName.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    
    // Apply sorting
    filtered = [...filtered].sort((a, b) => {
      let aVal: any = a[sortField as keyof typeof a];
      let bVal: any = b[sortField as keyof typeof b];
      
      // Handle different data types
      if (sortField === 'timestamp') {
        aVal = new Date(aVal).getTime();
        bVal = new Date(bVal).getTime();
      } else if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }
      
      if (sortDirection === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });
    
    return filtered;
  }, [trades, selectedAgent, searchTerm, sortField, sortDirection]);

  // Pagination
  const totalPages = Math.ceil(processedTrades.length / itemsPerPage);
  const paginatedTrades = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return processedTrades.slice(startIndex, startIndex + itemsPerPage);
  }, [processedTrades, currentPage]);

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
    setCurrentPage(1); // Reset to first page when sorting
  };

  const getSortIcon = (field: string) => {
    if (sortField !== field) {
      return <span className="text-gray-300 ml-1">⇅</span>;
    }
    return sortDirection === 'asc' 
      ? <span className="text-blue-600 ml-1">↑</span> 
      : <span className="text-blue-600 ml-1">↓</span>;
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-6">
        <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
          <span className="bg-blue-100 text-blue-800 p-2 rounded-lg mr-3">📊</span>
          Recent Trades
        </h3>
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto"></div>
          <p className="text-gray-500 mt-3">Loading trades...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-6">
        <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
          <span className="bg-blue-100 text-blue-800 p-2 rounded-lg mr-3">📊</span>
          Recent Trades
        </h3>
        <div className="text-center py-12">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md mx-auto">
            <p className="text-red-600">Error loading trades: {error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-6">
      {/* Header with filters */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 space-y-4 sm:space-y-0">
        <h3 className="text-xl font-bold text-gray-800 flex items-center">
          <span className="bg-blue-100 text-blue-800 p-2 rounded-lg mr-3">📊</span>
          Recent Trades
        </h3>
        
        <div className="flex flex-col sm:flex-row items-start sm:items-center space-y-2 sm:space-y-0 sm:space-x-4">
          {/* Search input */}
          <div className="relative">
            <input
              type="text"
              placeholder="Search symbol, rationale..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="px-4 py-2 pl-10 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 w-64"
            />
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <span className="text-gray-400">🔍</span>
            </div>
          </div>
          
          {/* Agent filter dropdown */}
          <select
            value={selectedAgent}
            onChange={(e) => {
              setSelectedAgent(e.target.value);
              setCurrentPage(1);
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white shadow-sm"
          >
            <option value="all">All Agents ({trades.length})</option>
            {uniqueAgents.map(agent => (
              <option key={agent} value={agent}>
                {agent} ({trades.filter(t => t.agentName === agent).length})
              </option>
            ))}
          </select>
        </div>
      </div>

      {processedTrades.length === 0 ? (
        <div className="text-center py-12">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 max-w-md mx-auto">
            <p className="text-gray-500">
              {selectedAgent === 'all' && !searchTerm 
                ? 'No recent trades found' 
                : 'No trades found matching your filters'}
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* Fancy Table */}
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full bg-white">
              <thead className="bg-gradient-to-r from-gray-50 to-blue-50">
                <tr>
                  <th 
                    className="px-6 py-4 text-left text-sm font-semibold text-gray-700 cursor-pointer hover:bg-blue-100 transition-colors select-none"
                    onClick={() => handleSort('agentName')}
                  >
                    <div className="flex items-center">
                      Agent{getSortIcon('agentName')}
                    </div>
                  </th>
                  <th 
                    className="px-6 py-4 text-left text-sm font-semibold text-gray-700 cursor-pointer hover:bg-blue-100 transition-colors select-none"
                    onClick={() => handleSort('transactionType')}
                  >
                    <div className="flex items-center">
                      Type{getSortIcon('transactionType')}
                    </div>
                  </th>
                  <th 
                    className="px-6 py-4 text-left text-sm font-semibold text-gray-700 cursor-pointer hover:bg-blue-100 transition-colors select-none"
                    onClick={() => handleSort('symbol')}
                  >
                    <div className="flex items-center">
                      Symbol{getSortIcon('symbol')}
                    </div>
                  </th>
                  <th 
                    className="px-6 py-4 text-right text-sm font-semibold text-gray-700 cursor-pointer hover:bg-blue-100 transition-colors select-none"
                    onClick={() => handleSort('quantity')}
                  >
                    <div className="flex items-center justify-end">
                      Qty{getSortIcon('quantity')}
                    </div>
                  </th>
                  <th 
                    className="px-6 py-4 text-right text-sm font-semibold text-gray-700 cursor-pointer hover:bg-blue-100 transition-colors select-none"
                    onClick={() => handleSort('price')}
                  >
                    <div className="flex items-center justify-end">
                      Price{getSortIcon('price')}
                    </div>
                  </th>
                  <th 
                    className="px-6 py-4 text-right text-sm font-semibold text-gray-700 cursor-pointer hover:bg-blue-100 transition-colors select-none"
                    onClick={() => handleSort('totalAmount')}
                  >
                    <div className="flex items-center justify-end">
                      Total{getSortIcon('totalAmount')}
                    </div>
                  </th>
                  <th 
                    className="px-6 py-4 text-left text-sm font-semibold text-gray-700 cursor-pointer hover:bg-blue-100 transition-colors select-none"
                    onClick={() => handleSort('timestamp')}
                  >
                    <div className="flex items-center">
                      Time{getSortIcon('timestamp')}
                    </div>
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">
                    Rationale
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {paginatedTrades.map((trade, index) => (
                  <tr 
                    key={`${trade.agentName}-${trade.timestamp}-${index}`} 
                    className="hover:bg-blue-50 transition-colors duration-150"
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-sm">
                          {trade.agentName.charAt(0)}
                        </div>
                        <span className="font-medium text-gray-900">{trade.agentName}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-3 py-1 rounded-full text-xs font-bold shadow-sm ${
                        trade.transactionType === 'BUY' 
                          ? 'bg-gradient-to-r from-green-400 to-green-600 text-white' 
                          : 'bg-gradient-to-r from-red-400 to-red-600 text-white'
                      }`}>
                        {trade.transactionType}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex items-center px-3 py-1 rounded-md text-sm font-mono font-bold text-gray-900 bg-gray-100 border border-gray-200">
                        {trade.symbol}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <span className="text-sm font-semibold text-gray-900">
                        {trade.quantity.toLocaleString()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <span className="text-sm font-semibold text-gray-900">
                        {formatPrice(trade.price)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <span className="inline-flex items-center px-3 py-1 rounded-md text-sm font-bold text-gray-900 bg-yellow-100 border border-yellow-200">
                        {formatTotal(trade.totalAmount)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="inline-flex items-center px-2 py-1 rounded-md text-xs text-gray-600 bg-gray-100 border border-gray-200">
                        {formatTimestamp(trade.timestamp)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div 
                        className="text-sm text-gray-600 bg-blue-50 px-3 py-2 rounded-md border border-blue-100 max-w-xs truncate" 
                        title={trade.rationale}
                      >
                        {trade.rationale}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-6">
              <div className="text-sm text-gray-600">
                Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, processedTrades.length)} of {processedTrades.length} trades
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                
                <div className="flex items-center space-x-1">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const pageNum = i + 1;
                    return (
                      <button
                        key={pageNum}
                        onClick={() => setCurrentPage(pageNum)}
                        className={`px-3 py-2 text-sm font-medium rounded-md ${
                          currentPage === pageNum
                            ? 'bg-blue-600 text-white'
                            : 'text-gray-500 bg-white border border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                  {totalPages > 5 && (
                    <>
                      <span className="text-gray-400">...</span>
                      <button
                        onClick={() => setCurrentPage(totalPages)}
                        className={`px-3 py-2 text-sm font-medium rounded-md ${
                          currentPage === totalPages
                            ? 'bg-blue-600 text-white'
                            : 'text-gray-500 bg-white border border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        {totalPages}
                      </button>
                    </>
                  )}
                </div>
                
                <button
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
      
      {/* Enhanced Stats footer */}
      <div className="mt-6 bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg p-4 border border-gray-100">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between space-y-2 sm:space-y-0">
          <div className="flex items-center space-x-6 text-sm">
            <div className="text-gray-600">
              <span className="font-semibold text-gray-800">{processedTrades.length}</span> of{' '}
              <span className="font-semibold text-gray-800">{trades.length}</span> trades
              {selectedAgent !== 'all' && <span className="text-blue-600 font-medium"> for {selectedAgent}</span>}
            </div>
            <div className="text-gray-600">
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                {processedTrades.filter(t => t.transactionType === 'BUY').length} BUY
              </span>
              <span className="mx-2">•</span>
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                {processedTrades.filter(t => t.transactionType === 'SELL').length} SELL
              </span>
            </div>
          </div>
          <div className="flex items-center space-x-4 text-xs text-gray-500">
            <span className="flex items-center">
              <span className="w-2 h-2 bg-blue-500 rounded-full mr-1"></span>
              Auto-refreshes every 15s
            </span>
            <span>💡 Click headers to sort</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RecentTrades;