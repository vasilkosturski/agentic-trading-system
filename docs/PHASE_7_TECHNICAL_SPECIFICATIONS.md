# Phase 7.1 Technical Specifications
*Portfolio Performance Charts - Detailed Implementation Guide*

## Overview

This document contains the comprehensive technical specifications for **Phase 7.1: Portfolio Performance Charts** of the Agentic Trading System. These specifications were extracted from the main implementation plan to maintain clarity and focus.

**Related Documents:**
- Main Implementation Plan: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)
- Database Documentation: [`../database/README.md`](../database/README.md)
- Docker Setup Guide: [`../README-Docker.md`](../README-Docker.md)

---

## Portfolio Performance Charts Implementation

**Goal**: Implement comprehensive portfolio performance visualization with historical time-series charts showing portfolio value trends, P&L analysis, and comparative performance metrics across all 4 trading agents.

**Duration**: 5-7 days

### Database Requirements ✅ *Mostly Complete*

**Existing Infrastructure:**
- ✅ `trading.account_portfolio_snapshots` table with time-series data structure
- ✅ Automated snapshot creation on every transaction via `createPortfolioSnapshot()`
- ✅ `AccountPortfolioSnapshotRepository` with performance query methods

**Additional Database Enhancements Needed:**
```sql
-- 1. Add performance calculation indexes for faster queries
CREATE INDEX CONCURRENTLY idx_portfolio_snapshots_account_timestamp
ON trading.account_portfolio_snapshots(account_id, timestamp);

-- 2. Add materialized view for daily performance aggregation
CREATE MATERIALIZED VIEW analytics.daily_portfolio_performance AS
SELECT
    account_id,
    DATE(timestamp) as performance_date,
    MIN(total_value) as day_low,
    MAX(total_value) as day_high,
    FIRST_VALUE(total_value ORDER BY timestamp) as day_open,
    LAST_VALUE(total_value ORDER BY timestamp) as day_close,
    AVG(total_value) as day_average,
    COUNT(*) as snapshot_count
FROM trading.account_portfolio_snapshots
GROUP BY account_id, DATE(timestamp)
ORDER BY account_id, performance_date;

-- 3. Add refresh function for materialized view
CREATE OR REPLACE FUNCTION refresh_daily_performance()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.daily_portfolio_performance;
END;
$$ LANGUAGE plpgsql;
```

**Data Collection Strategy:**
- ✅ **Transaction-based**: Snapshots created automatically on every buy/sell transaction
- 🆕 **Scheduled snapshots**: Add hourly snapshots during market hours for smoother charts
- 🆕 **Daily snapshots**: End-of-day portfolio snapshots for daily performance tracking
- 🆕 **Backfill mechanism**: Generate historical snapshots for existing accounts

### Backend API Requirements

**New REST Endpoints:**
```java
// 1. Portfolio Performance Time Series
GET /api/portfolio/{agentName}/performance
    ?period={1D|7D|1M|3M|6M|1Y|ALL}
    &granularity={HOURLY|DAILY|WEEKLY}
    &includeMetrics={true|false}

// 2. Comparative Performance (All Agents)
GET /api/portfolio/performance/comparative
    ?period={1D|7D|1M|3M|6M|1Y|ALL}
    &normalize={true|false}  // Normalize to percentage returns

// 3. Portfolio Performance Metrics
GET /api/portfolio/{agentName}/metrics
    ?period={1D|7D|1M|3M|6M|1Y|ALL}

// 4. Portfolio Performance Summary
GET /api/portfolio/performance/summary
```

**New Java Service Methods:**
```java
// In PostgreSQLAccountService.java or new PortfolioPerformanceService.java

public class PortfolioPerformanceService {
    
    // 1. Get time-series performance data
    public PortfolioPerformanceResponse getPortfolioPerformance(
        String agentName,
        TimePeriod period,
        Granularity granularity
    );
    
    // 2. Get comparative performance across all agents
    public ComparativePerformanceResponse getComparativePerformance(
        TimePeriod period,
        boolean normalize
    );
    
    // 3. Calculate performance metrics
    public PerformanceMetrics calculatePerformanceMetrics(
        String agentName,
        TimePeriod period
    );
    
    // 4. Generate scheduled snapshots
    @Scheduled(fixedRate = 3600000) // Every hour
    public void createScheduledSnapshots();
    
    // 5. Backfill historical data
    public void backfillHistoricalSnapshots(String agentName, LocalDateTime fromDate);
}
```

**Data Transfer Objects:**
```java
public class PortfolioPerformanceResponse {
    private String agentName;
    private List<PerformanceDataPoint> dataPoints;
    private PerformanceMetrics metrics;
    private TimePeriod period;
    private Granularity granularity;
}

public class PerformanceDataPoint {
    private LocalDateTime timestamp;
    private Double portfolioValue;
    private Double cashBalance;
    private Double holdingsValue;
    private Double totalPnL;
    private Double dailyPnL;
    private Double returnPercent;
}

public class PerformanceMetrics {
    private Double totalReturn;
    private Double annualizedReturn;
    private Double volatility;
    private Double sharpeRatio;
    private Double maxDrawdown;
    private Double winRate;
    private Integer totalTrades;
    private Double bestDay;
    private Double worstDay;
}

public class ComparativePerformanceResponse {
    private Map<String, List<PerformanceDataPoint>> agentPerformance;
    private Map<String, PerformanceMetrics> agentMetrics;
    private TimePeriod period;
    private boolean normalized;
}
```

### Frontend Implementation

**React Component Structure:**
```typescript
// 1. Main Portfolio Charts Container
src/components/PortfolioCharts/
├── PortfolioChartsContainer.tsx          // Main container component
├── PerformanceChart.tsx                  // Individual agent performance chart
├── ComparativeChart.tsx                  // All agents comparison chart
├── MetricsPanel.tsx                      // Performance metrics display
├── ChartControls.tsx                     // Time period and granularity controls
├── ChartLegend.tsx                       // Chart legend and agent colors
└── types.ts                              // TypeScript interfaces

// 2. Chart Configuration
src/config/chartConfig.ts                 // Recharts configuration and themes
```

**Key React Components:**

**PortfolioChartsContainer.tsx:**
```typescript
interface PortfolioChartsContainerProps {
  selectedAgent?: string;
  showComparative?: boolean;
}

const PortfolioChartsContainer: React.FC<PortfolioChartsContainerProps> = ({
  selectedAgent,
  showComparative = false
}) => {
  const [timePeriod, setTimePeriod] = useState<TimePeriod>('1M');
  const [granularity, setGranularity] = useState<Granularity>('DAILY');
  const [chartType, setChartType] = useState<'line' | 'area'>('area');
  
  // React Query hooks for data fetching
  const { data: performanceData } = usePortfolioPerformance(selectedAgent, timePeriod, granularity);
  const { data: comparativeData } = useComparativePerformance(timePeriod, showComparative);
  
  return (
    <div className="portfolio-charts-container">
      <ChartControls
        timePeriod={timePeriod}
        onTimePeriodChange={setTimePeriod}
        granularity={granularity}
        onGranularityChange={setGranularity}
        chartType={chartType}
        onChartTypeChange={setChartType}
      />
      
      {showComparative ? (
        <ComparativeChart
          data={comparativeData}
          chartType={chartType}
        />
      ) : (
        <PerformanceChart
          agentName={selectedAgent}
          data={performanceData}
          chartType={chartType}
        />
      )}
      
      <MetricsPanel
        agentName={selectedAgent}
        metrics={performanceData?.metrics}
      />
    </div>
  );
};
```

**PerformanceChart.tsx (Using Recharts):**
```typescript
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const PerformanceChart: React.FC<PerformanceChartProps> = ({
  agentName,
  data,
  chartType = 'area'
}) => {
  const chartData = data?.dataPoints?.map(point => ({
    timestamp: new Date(point.timestamp).getTime(),
    portfolioValue: point.portfolioValue,
    totalPnL: point.totalPnL,
    returnPercent: point.returnPercent,
    formattedDate: formatDate(point.timestamp)
  }));

  const ChartComponent = chartType === 'area' ? AreaChart : LineChart;
  const DataComponent = chartType === 'area' ? Area : Line;

  return (
    <div className="performance-chart">
      <div className="chart-header">
        <h3>{agentName} Portfolio Performance</h3>
        <div className="chart-metrics">
          <span className={`total-return ${data?.metrics?.totalReturn >= 0 ? 'positive' : 'negative'}`}>
            {formatPercent(data?.metrics?.totalReturn)}
          </span>
        </div>
      </div>
      
      <ResponsiveContainer width="100%" height={400}>
        <ChartComponent data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="timestamp"
            type="number"
            scale="time"
            domain={['dataMin', 'dataMax']}
            tickFormatter={(value) => formatDate(new Date(value))}
          />
          <YAxis
            domain={['dataMin - 1000', 'dataMax + 1000']}
            tickFormatter={(value) => formatCurrency(value)}
          />
          <Tooltip
            labelFormatter={(value) => formatDate(new Date(value))}
            formatter={(value, name) => [formatCurrency(value), name]}
          />
          <DataComponent
            type="monotone"
            dataKey="portfolioValue"
            stroke={getAgentColor(agentName)}
            fill={getAgentColor(agentName)}
            fillOpacity={chartType === 'area' ? 0.3 : 0}
            strokeWidth={2}
          />
        </ChartComponent>
      </ResponsiveContainer>
    </div>
  );
};
```

**Data Fetching Hooks:**
```typescript
// src/hooks/usePortfolioPerformance.ts
export const usePortfolioPerformance = (
  agentName: string,
  period: TimePeriod,
  granularity: Granularity
) => {
  return useQuery({
    queryKey: ['portfolioPerformance', agentName, period, granularity],
    queryFn: () => portfolioApi.getPerformance(agentName, period, granularity),
    refetchInterval: 60000, // Refetch every minute
    staleTime: 30000, // Consider data stale after 30 seconds
  });
};

// src/hooks/useComparativePerformance.ts
export const useComparativePerformance = (period: TimePeriod, enabled: boolean) => {
  return useQuery({
    queryKey: ['comparativePerformance', period],
    queryFn: () => portfolioApi.getComparativePerformance(period),
    enabled,
    refetchInterval: 60000,
  });
};
```

### Integration Points

**1. Agent Monitoring Integration:**
- Extend existing `AgentMonitoringService` to include performance chart data
- Add performance charts to individual agent detail pages
- Integrate with existing agent status API for real-time updates

**2. Real-time vs Historical Data:**
- **Real-time**: Use existing 15-second refresh cycle for current portfolio values
- **Historical**: Cache historical performance data with 1-minute refresh interval
- **Hybrid approach**: Show real-time current value with historical trend line

**3. Dashboard Integration:**
- Add performance chart widgets to main trading dashboard
- Implement expandable chart views with drill-down capabilities
- Add performance comparison mode for all 4 agents

### Performance Considerations

**Database Optimization:**
- Use materialized views for pre-aggregated daily performance data
- Implement database connection pooling for chart data queries
- Add query result caching with Redis (optional enhancement)

**Frontend Optimization:**
- Implement data virtualization for large time series datasets
- Use React.memo for chart components to prevent unnecessary re-renders
- Implement progressive data loading (load recent data first, then historical)

**API Optimization:**
- Add response compression for large time series datasets
- Implement pagination for very large date ranges
- Use HTTP caching headers for historical data that doesn't change

### Implementation Steps

**Phase 7.1.1: Database Enhancements (1 day)** 📋 **IMPLEMENTATION GUIDE READY**
- **Status**: 📋 **IMPLEMENTATION GUIDE COMPLETED** - Comprehensive guide available at [`roo-context/output/explanations/phase-7-1-1-database-implementation-guide.md`](../../roo-context/output/explanations/phase-7-1-1-database-implementation-guide.md)
- **Guide Contents**:
  - ✅ **Current State Analysis**: Detailed analysis of existing PostgreSQL schema and portfolio snapshots
  - ✅ **Step-by-Step Implementation**: Complete migration script structure and database enhancements
  - ✅ **Performance Optimization**: Indexes, materialized views, and stored procedures specifications
  - ✅ **Testing Strategy**: Unit tests, integration tests, and performance benchmarks
  - ✅ **Risk Mitigation**: Rollback plans and success criteria
  - ✅ **Timeline**: Day 1 implementation schedule with morning/afternoon/evening tasks
- **Implementation Tasks**:
  1. Create performance indexes and materialized views
  2. Implement scheduled snapshot creation service
  3. Add backfill mechanism for historical data
  4. Test database performance with large datasets
- **Ready for Implementation**: All specifications, SQL examples, and validation steps documented

**Phase 7.1.2: Backend API Development (2 days)**
1. Create `PortfolioPerformanceService` with all required methods
2. Implement REST endpoints for performance data
3. Add DTOs for performance data transfer
4. Implement caching strategy for performance queries
5. Add comprehensive error handling and validation

**Phase 7.1.3: Frontend Chart Components (2 days)**
1. Create React component structure for portfolio charts
2. Implement `PerformanceChart` component with Recharts
3. Create `ComparativeChart` for multi-agent comparison
4. Add chart controls for time period and granularity selection
5. Implement responsive design for mobile devices

**Phase 7.1.4: Integration and Testing (1 day)**
1. Integrate charts with existing dashboard
2. Add performance charts to agent detail pages
3. Test real-time data updates and chart responsiveness
4. Implement error handling and loading states
5. Performance testing with large datasets

**Phase 7.1.5: UI/UX Polish and Documentation (1 day)**
1. Add chart animations and smooth transitions
2. Implement chart export functionality (PNG/PDF)
3. Add tooltips and help text for chart interpretation
4. Create user documentation for chart features
5. Final testing and bug fixes

### Testing Strategy

**Unit Tests:**
- Test performance calculation methods in `PortfolioPerformanceService`
- Test React chart components with mock data
- Test data transformation and formatting utilities

**Integration Tests:**
- Test API endpoints with real database data
- Test chart rendering with various data scenarios
- Test real-time data updates and chart refresh

**Performance Tests:**
- Load test with 1 year of hourly snapshots (8,760 data points)
- Test chart rendering performance with large datasets
- Database query performance testing

### Rollback Plan

**If Implementation Issues Arise:**
1. **Database rollback**: Remove new indexes and materialized views
2. **API rollback**: Disable new endpoints, fall back to existing agent status API
3. **Frontend rollback**: Hide chart components, show existing portfolio summary
4. **Gradual rollout**: Enable charts for one agent at a time for testing

**Success Criteria:**
- ✅ Charts load within 2 seconds for 30-day data
- ✅ Real-time updates work smoothly without performance impact
- ✅ All 4 agents can display performance charts simultaneously
- ✅ Charts are responsive and work on mobile devices
- ✅ Historical data backfill completes successfully for existing accounts

---

## Summary

This technical specification document provides comprehensive implementation details for **Phase 7.1: Portfolio Performance Charts** of the Agentic Trading System. It includes detailed technical requirements, implementation steps, and success criteria to ensure successful delivery of portfolio performance visualization capabilities.

**Estimated Duration**: 5-7 days
**Priority**: High (Core dashboard enhancement)
**Dependencies**: Phases 1-6 must be completed
**Risk Level**: Medium (UI/UX focused with existing backend foundation)

**Key Deliverables**:
- Historical portfolio performance charts with time-series data
- Comparative performance visualization across all 4 trading agents
- Real-time performance metrics and analytics
- Interactive chart controls and responsive design
- Database optimizations for performance data queries