import React, { useState, useMemo } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Dropdown } from 'primereact/dropdown';
import { InputText } from 'primereact/inputtext';
import { Tag } from 'primereact/tag';
import { useRecentTrades } from '../../hooks/useRecentTrades';
import { RecentTrade } from '../../services/tradesService';

// Import PrimeReact CSS
import 'primereact/resources/themes/lara-light-blue/theme.css';
import 'primereact/resources/primereact.min.css';
import 'primeicons/primeicons.css';

const RecentTrades: React.FC = () => {
  const { trades, loading, error } = useRecentTrades(50);
  const [selectedAgent, setSelectedAgent] = useState<string>('all');
  const [globalFilter, setGlobalFilter] = useState<string>('');

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
    return [
      { label: `All Agents (${trades.length})`, value: 'all' },
      ...agents.map(agent => ({
        label: `${agent} (${trades.filter(t => t.agentName === agent).length})`,
        value: agent
      }))
    ];
  }, [trades]);

  // Filter trades based on selected agent
  const filteredTrades = useMemo(() => {
    if (selectedAgent === 'all') return trades;
    return trades.filter(trade => trade.agentName === selectedAgent);
  }, [trades, selectedAgent]);

  // Custom column renderers
  const agentBodyTemplate = (rowData: RecentTrade) => {
    return (
      <div className="flex items-center space-x-2">
        <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-xs font-bold">
          {rowData.agentName.charAt(0)}
        </div>
        <span className="font-medium">{rowData.agentName}</span>
      </div>
    );
  };

  const typeBodyTemplate = (rowData: RecentTrade) => {
    return (
      <Tag 
        value={rowData.transactionType} 
        severity={rowData.transactionType === 'BUY' ? 'success' : 'danger'}
        className="font-bold"
      />
    );
  };

  const symbolBodyTemplate = (rowData: RecentTrade) => {
    return (
      <span className="inline-flex items-center px-3 py-1 rounded-md text-sm font-mono font-bold text-gray-900 bg-gray-100 border border-gray-200">
        {rowData.symbol}
      </span>
    );
  };

  const quantityBodyTemplate = (rowData: RecentTrade) => {
    return <span className="font-semibold">{rowData.quantity.toLocaleString()}</span>;
  };

  const priceBodyTemplate = (rowData: RecentTrade) => {
    return <span className="font-semibold">{formatPrice(rowData.price)}</span>;
  };

  const totalBodyTemplate = (rowData: RecentTrade) => {
    return (
      <span className="inline-flex items-center px-3 py-1 rounded-md text-sm font-bold text-gray-900 bg-yellow-100 border border-yellow-200">
        {formatTotal(rowData.totalAmount)}
      </span>
    );
  };

  const timeBodyTemplate = (rowData: RecentTrade) => {
    return (
      <div className="inline-flex items-center px-2 py-1 rounded-md text-xs text-gray-600 bg-gray-100 border border-gray-200">
        {formatTimestamp(rowData.timestamp)}
      </div>
    );
  };

  const rationaleBodyTemplate = (rowData: RecentTrade) => {
    return (
      <div 
        className="text-sm text-gray-600 bg-blue-50 px-3 py-2 rounded-md border border-blue-100 max-w-xs truncate" 
        title={rowData.rationale}
      >
        {rowData.rationale}
      </div>
    );
  };

  const header = (
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between space-y-4 sm:space-y-0 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-t-lg">
      <div className="flex items-center space-x-3">
        <span className="bg-blue-100 text-blue-800 p-2 rounded-lg text-lg">📊</span>
        <h3 className="text-xl font-bold text-gray-800">Recent Trades</h3>
      </div>
      
      <div className="flex flex-col sm:flex-row items-start sm:items-center space-y-2 sm:space-y-0 sm:space-x-4">
        <div className="flex items-center space-x-2">
          <label htmlFor="global-search" className="text-sm font-medium text-gray-600">
            Search:
          </label>
          <InputText
            id="global-search"
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder="Search trades..."
            className="p-inputtext-sm"
          />
        </div>
        
        <div className="flex items-center space-x-2">
          <label htmlFor="agent-filter" className="text-sm font-medium text-gray-600">
            Agent:
          </label>
          <Dropdown
            id="agent-filter"
            value={selectedAgent}
            options={uniqueAgents}
            onChange={(e) => setSelectedAgent(e.value)}
            className="p-dropdown-sm"
            style={{ minWidth: '150px' }}
          />
        </div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-6">
        <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
          <span className="bg-blue-100 text-blue-800 p-2 rounded-lg mr-3">📊</span>
          Recent Trades
        </h3>
        <div className="text-center py-12">
          <i className="pi pi-spin pi-spinner text-4xl text-blue-600"></i>
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
            <i className="pi pi-exclamation-triangle text-red-500 text-2xl mb-2"></i>
            <p className="text-red-600">Error loading trades: {error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
        <DataTable
          value={filteredTrades}
          header={header}
          globalFilter={globalFilter}
          paginator
          rows={10}
          rowsPerPageOptions={[5, 10, 15, 20]}
          sortMode="multiple"
          removableSort
          filterDisplay="row"
          emptyMessage="No trades found matching your criteria"
          className="p-datatable-sm"
          stripedRows
          showGridlines
          responsiveLayout="scroll"
        >
          <Column 
            field="agentName" 
            header="Agent" 
            sortable 
            filter 
            filterPlaceholder="Filter by agent"
            body={agentBodyTemplate}
            style={{ minWidth: '150px' }}
          />
          <Column 
            field="transactionType" 
            header="Type" 
            sortable 
            filter 
            filterPlaceholder="BUY/SELL"
            body={typeBodyTemplate}
            style={{ minWidth: '100px' }}
          />
          <Column 
            field="symbol" 
            header="Symbol" 
            sortable 
            filter 
            filterPlaceholder="Filter by symbol"
            body={symbolBodyTemplate}
            style={{ minWidth: '120px' }}
          />
          <Column 
            field="quantity" 
            header="Qty" 
            sortable 
            body={quantityBodyTemplate}
            style={{ minWidth: '80px', textAlign: 'right' }}
          />
          <Column 
            field="price" 
            header="Price" 
            sortable 
            body={priceBodyTemplate}
            style={{ minWidth: '100px', textAlign: 'right' }}
          />
          <Column 
            field="totalAmount" 
            header="Total" 
            sortable 
            body={totalBodyTemplate}
            style={{ minWidth: '120px', textAlign: 'right' }}
          />
          <Column 
            field="timestamp" 
            header="Time" 
            sortable 
            body={timeBodyTemplate}
            style={{ minWidth: '140px' }}
          />
          <Column 
            field="rationale" 
            header="Rationale" 
            sortable 
            filter 
            filterPlaceholder="Filter by rationale"
            body={rationaleBodyTemplate}
            style={{ minWidth: '250px' }}
          />
        </DataTable>
      </div>
      
      {/* Enhanced Stats footer */}
      <div className="mt-4 bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg p-4 border border-gray-100">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between space-y-2 sm:space-y-0">
          <div className="flex items-center space-x-6 text-sm">
            <div className="text-gray-600">
              <span className="font-semibold text-gray-800">{filteredTrades.length}</span> of{' '}
              <span className="font-semibold text-gray-800">{trades.length}</span> trades
              {selectedAgent !== 'all' && <span className="text-blue-600 font-medium"> for {selectedAgent}</span>}
            </div>
            <div className="text-gray-600">
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                {filteredTrades.filter(t => t.transactionType === 'BUY').length} BUY
              </span>
              <span className="mx-2">•</span>
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                {filteredTrades.filter(t => t.transactionType === 'SELL').length} SELL
              </span>
            </div>
          </div>
          <div className="flex items-center space-x-4 text-xs text-gray-500">
            <span className="flex items-center">
              <i className="pi pi-refresh mr-1"></i>
              Auto-refreshes every 15s
            </span>
            <span className="flex items-center">
              <i className="pi pi-search mr-1"></i>
              Use search and filters above
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RecentTrades;