# Phase 7.1 Technical Specifications - SIMPLIFIED
*Simple Portfolio Value Graphs - Basic Implementation Guide*

## Overview

Add basic portfolio value line charts below each agent card on the main dashboard showing portfolio value trends over time.

**Duration**: 2-3 days  
**Location**: Below each agent card in [`TradingDashboard.tsx`](../frontend/src/components/TradingDashboard/TradingDashboard.tsx)

---

## Backend Requirements ✅ *REUSE EXISTING*

**Existing Infrastructure (No Changes Needed):**
- ✅ `account_portfolio_snapshots` table with transaction-based snapshots
- ✅ `AccountPortfolioSnapshotRepository.getPortfolioPerformance()` method already exists
- ✅ Snapshots automatically created on every trade via `createPortfolioSnapshot()`

**New API Endpoint Needed:**
```java
// Add to AccountController.java
@GetMapping("/portfolio/{agentName}/history")
public ResponseEntity<List<PortfolioHistoryPoint>> getPortfolioHistory(
    @PathVariable String agentName,
    @RequestParam(defaultValue = "7") int days
) {
    // Use existing repository method
    LocalDateTime fromDate = LocalDateTime.now().minusDays(days);
    List<AccountPortfolioSnapshot> snapshots = snapshotRepository
        .getPortfolioPerformance(agentName, fromDate);
    
    // Convert to simple DTO
    List<PortfolioHistoryPoint> history = snapshots.stream()
        .map(s -> new PortfolioHistoryPoint(s.getTimestamp(), s.getTotalValue()))
        .collect(Collectors.toList());
    
    return ResponseEntity.ok(history);
}
```

**Simple DTO:**
```java
public class PortfolioHistoryPoint {
    private LocalDateTime timestamp;
    private Double portfolioValue;
    // constructors, getters, setters
}
```

---

## Frontend Requirements

**Files to Create/Modify:**
- `TradingDashboard.tsx` - Add chart below each agent card
- `SimplePortfolioChart.tsx` - New basic chart component  
- `usePortfolioHistory.ts` - New hook for data fetching
- `portfolioService.ts` - New API service

**Implementation:**
1. **Chart Component**: Simple Recharts LineChart (120px height)
2. **Data Fetching**: React Query hook calling `/api/accounts/portfolio/{agent}/history?days=7`
3. **Integration**: Add chart below existing agent card content
4. **Styling**: Minimal styling to fit within existing card design

---

## Implementation Steps

**Day 1: Backend (4 hours)**
1. Add `PortfolioHistoryPoint` DTO class
2. Add `/portfolio/{agentName}/history` endpoint to `AccountController`
3. Test endpoint with existing portfolio snapshot data

**Day 2: Frontend (6 hours)**  
1. Install Recharts: `npm install recharts`
2. Create `SimplePortfolioChart` component
3. Create `usePortfolioHistory` hook and `portfolioService`
4. Integrate charts into `TradingDashboard` component

**Day 3: Polish (2 hours)**
1. Test with real data and adjust styling
2. Handle edge cases (no data, loading states)
3. Responsive design verification

---

## Success Criteria

- ✅ Simple line charts appear below each of the 4 agent cards
- ✅ Charts show portfolio value over the last 7 days  
- ✅ Charts update automatically every minute
- ✅ No performance impact on dashboard loading
- ✅ Graceful handling when no historical data available

---

## Key Simplifications

**✅ Reusing Existing Backend:**
- No new database tables or migrations needed
- Leveraging existing `AccountPortfolioSnapshotRepository.getPortfolioPerformance()`
- Using existing transaction-based portfolio snapshots

**✅ Minimal Frontend Scope:**
- Basic line charts only (no complex analytics)
- Fixed 7-day period (no time controls)
- Charts embedded in existing agent cards (no separate pages)
- Simple Recharts implementation (no custom chart libraries)