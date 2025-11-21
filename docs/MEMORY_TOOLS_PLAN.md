# Memory Tools Implementation Plan

**Status**: Planning Phase  
**Objective**: Add dynamic memory retrieval for agent decision-making  
**Approach**: Deterministic SQL queries via @function_tools

---

## 1. Problem Statement

### Current State
- Agent gets: Strategy + Current Account + Tools
- Agent doesn't see: Past reasoning, conviction levels, thesis evolution
- Result: Agent can't learn from own past decisions

### Desired State
- Agent gets: Same as above PLUS access to memory tools
- Agent can query: "What did I think about NVDA before?"
- Agent can reason: "My thesis was X, has it changed?"
- Result: True learning loop

---

## 2. Solution Architecture

### Memory as Tools (Not Context)

**Why this approach?**
```
Static Context Injection (BAD):
├─ Load all history upfront
├─ Clutter context window
└─ Agent can't control what's relevant

Dynamic Tool Calls (GOOD):
├─ Agent queries on-demand
├─ Only retrieves when needed
├─ Agent decides relevance
└─ Follows same pattern as Researcher tool
```

### 4 Memory Tools

```
Tool 1: get_prior_research(symbol)
├─ Query: Past trades for this symbol
├─ Returns: Buy/sell history with reasoning
├─ Use case: "Should I add to NVDA?"

Tool 2: get_conviction_level(symbol)
├─ Query: Current conviction level
├─ Returns: High/Medium/Low
├─ Use case: "How confident am I about this stock?"

Tool 3: get_recent_decisions(days=7)
├─ Query: Recent trading activity
├─ Returns: Symbols traded, reasoning, outcomes
├─ Use case: "What have I been doing?"

Tool 4: analyze_thesis_change(symbol)
├─ Query: Thesis evolution over time
├─ Returns: Timeline of conviction changes
├─ Use case: "How has my view of this stock changed?"
```

---

## 3. Implementation Details

### File: `agents/memory_tools.py` (NEW)

```python
#!/usr/bin/env python3
"""
Memory tools for agents to query their past decisions and reasoning
Uses PostgreSQL directly via SQL queries
No external dependencies - pure SQL + formatting
"""

from agents import function_tool
from config import BACKEND_BASE_URL
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@function_tool
async def get_prior_research(symbol: str, agent_id: int) -> str:
    """Query past research about a specific stock
    
    Returns your trading history for this symbol including:
    - Buy/sell decisions
    - Entry and exit prices
    - Your reasoning at time of trade
    - Research sources you consulted
    - When trades were made
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'NVDA', 'GLD')
        agent_id: Your agent ID
        
    Returns:
        Formatted string with past research and decisions
        
    Example:
        "NVDA Trading History:
         - Bought 50 @ $207.04 on Oct 30, 2025
           Reasoning: Market leader in AI chips
           Sources: cnbc.com, reuters.com
         - No sells yet
         Current holding: 50 shares at +X% return"
    """
    query = """
    SELECT 
        transaction_type,
        quantity,
        price,
        timestamp,
        full_reasoning,
        research_sources
    FROM trading.account_transactions
    WHERE symbol = $1 
      AND account_id = (SELECT id FROM trading.trading_accounts WHERE agent_id = $2)
    ORDER BY timestamp DESC
    LIMIT 10
    """
    # Execute query, format results
    # Return: Narrative format with trading history
    pass

@function_tool
async def get_conviction_level(symbol: str, agent_id: int) -> str:
    """Check your conviction level for a stock
    
    Returns:
        - "HIGH": You've bought multiple times, thesis is strong
        - "MEDIUM": You've bought once, holding
        - "LOW": You've researched but not bought
        - "NOT RESEARCHED": No history with this stock
        
    Use this to:
        - Understand your confidence level
        - Decide if you should add to or exit positions
        - Gauge risk tolerance for this holding
    """
    query = """
    WITH trades AS (
        SELECT 
            symbol,
            transaction_type,
            quantity,
            full_reasoning
        FROM trading.account_transactions
        WHERE symbol = $1 
          AND account_id = (SELECT id FROM trading.trading_accounts WHERE agent_id = $2)
        ORDER BY timestamp DESC
    ),
    current_position AS (
        SELECT quantity FROM trading.account_holdings
        WHERE symbol = $1
          AND account_id = (SELECT id FROM trading.trading_accounts WHERE agent_id = $2)
    )
    SELECT 
        CASE 
            WHEN NOT EXISTS (SELECT 1 FROM trades) THEN 'NOT_RESEARCHED'
            WHEN (SELECT quantity FROM current_position) > 0 AND 
                 (SELECT COUNT(*) FROM trades WHERE transaction_type='BUY') > 1 THEN 'HIGH'
            WHEN (SELECT quantity FROM current_position) > 0 THEN 'MEDIUM'
            WHEN EXISTS (SELECT 1 FROM trades WHERE transaction_type='SELL') THEN 'LOW'
            ELSE 'LOW'
        END as conviction
    """
    # Execute query, return conviction level
    pass

@function_tool
async def get_recent_decisions(agent_id: int, days: int = 7) -> str:
    """See your recent trading activity
    
    Shows trades from the past N days including:
    - What you traded
    - Whether you bought or sold
    - Your reasoning for each decision
    - When each trade occurred
    
    Args:
        agent_id: Your agent ID
        days: How many days back (default: 7 days)
        
    Returns:
        Timeline of recent decisions and their reasoning
        
    Example:
        "Last 7 days:
         Oct 31: Bought 10 DKNG @ $30.14
           Why: Growth in gaming/sports betting
         Oct 30: Bought 100 GLD @ $363
           Why: Safe haven amid volatility
         Oct 30: Bought 10 NVDA @ $207.04
           Why: AI market leader, strong fundamentals"
    """
    query = """
    SELECT 
        symbol,
        transaction_type,
        quantity,
        price,
        timestamp,
        full_reasoning,
        rationale
    FROM trading.account_transactions
    WHERE account_id = (SELECT id FROM trading.trading_accounts WHERE agent_id = $1)
      AND timestamp > NOW() - INTERVAL $2 * INTERVAL '1 day'
    ORDER BY timestamp DESC
    """
    # Execute query, format as timeline
    pass

@function_tool
async def analyze_thesis_change(symbol: str, agent_id: int) -> str:
    """Track how your investment thesis has evolved
    
    Shows how your thinking about a stock has changed over time:
    - When you first researched it
    - Initial conviction level
    - How your reasoning evolved
    - Current conviction and status
    
    Use this to:
        - Understand if your thesis is strengthening or weakening
        - Decide to add, hold, or exit
        - Avoid repeating past mistakes
        
    Returns:
        Timeline of thesis evolution with dates and reasoning changes
        
    Example:
        "NVDA Thesis Evolution:
         Oct 15: RESEARCHED - 'Concerned about valuation'
                Conviction: LOW
         Oct 20: 'AI catalyst news positive'
                Conviction: MEDIUM (considering buy)
         Oct 30: BOUGHT 50 @ $207 - 'Market leader in AI'
                Conviction: HIGH
         Current: Holding 50 shares
                  Thesis: 'Still valid, AI tailwinds continue'"
    """
    query = """
    SELECT 
        timestamp,
        transaction_type,
        quantity,
        price,
        full_reasoning,
        (SELECT COUNT(*) FROM trading.account_transactions t2 
         WHERE t2.symbol = $1 AND t2.timestamp <= t1.timestamp
           AND account_id = (SELECT id FROM trading.trading_accounts WHERE agent_id = $2)) as action_count
    FROM trading.account_transactions t1
    WHERE symbol = $1 
      AND account_id = (SELECT id FROM trading.trading_accounts WHERE agent_id = $2)
    ORDER BY timestamp
    """
    # Execute query, format as evolution timeline
    pass
```

### Integration Points

**File: `agents/simple_trader.py`**

1. **Import memory tools** (top of file)
```python
from memory_tools import (
    get_prior_research,
    get_recent_decisions,
    get_conviction_level,
    analyze_thesis_change
)
```

2. **Add to agent tools** (in `create_agent()`)
```python
all_tools = [
    researcher_tool,
    *MARKET_TOOLS,
    get_prior_research,          # NEW
    get_recent_decisions,        # NEW
    get_conviction_level,        # NEW
    analyze_thesis_change,       # NEW
    decide_action
]
```

3. **Update agent instructions** (in `get_trader_instructions()`)
```python
def get_trader_instructions(self) -> str:
    return f"""
    ...existing instructions...
    
    MEMORY TOOLS - Query Your Past Decisions:
    - get_prior_research(symbol): See what you've researched about this stock
    - get_conviction_level(symbol): Check your confidence level
    - get_recent_decisions(days): See recent trades and reasoning
    - analyze_thesis_change(symbol): Track how your thinking has evolved
    
    Use these tools to:
    ✓ Understand your own convictions before trading
    ✓ Check if your thesis has changed since last decision
    ✓ Avoid repeating past mistakes
    ✓ Build consistency in your investment approach
    """
```

---

## 4. Data Flow

```
Agent Execution:
│
├─ Start: Agent gets strategy + current account + tools
│
├─ During Reasoning:
│  └─ Agent thinks: "Should I buy more NVDA?"
│  └─ Calls: get_prior_research("NVDA")
│  └─ Query: PostgreSQL → account_transactions table
│  └─ Returns: "Bought 50 @ $207, thesis: AI leader"
│  └─ Agent uses this in reasoning
│
├─ Decision: Agent decides to BUY/SELL/HOLD
│
└─ Storage: 
   └─ New trade stored with:
      ├─ full_reasoning
      ├─ research_sources
      └─ agent_context
   └─ Available for NEXT cycle's memory queries
```

---

## 5. SQL Queries Detail

### Query 1: get_prior_research

```sql
-- Get all trades for a symbol, ordered by recency
SELECT 
    transaction_type,           -- 'BUY' or 'SELL'
    quantity,                   -- shares
    price,                       -- entry/exit price
    timestamp,                   -- when trade occurred
    full_reasoning,              -- why agent decided
    research_sources             -- URLs researched
FROM trading.account_transactions
WHERE symbol = $1 
  AND account_id = $2
ORDER BY timestamp DESC
LIMIT 10;
```

### Query 2: get_conviction_level

```sql
-- Determine conviction based on trading history
CASE 
    WHEN NOT EXISTS (SELECT 1 FROM trades) 
        THEN 'NOT_RESEARCHED'
    WHEN holding_exists AND buy_count > 1 
        THEN 'HIGH'
    WHEN holding_exists 
        THEN 'MEDIUM'
    WHEN sold_before 
        THEN 'LOW'
    ELSE 'LOW'
END
```

### Query 3: get_recent_decisions

```sql
-- Get trades from last N days
SELECT 
    symbol, 
    transaction_type, 
    quantity, 
    price, 
    timestamp, 
    full_reasoning
FROM trading.account_transactions
WHERE account_id = $1
  AND timestamp > NOW() - INTERVAL N DAYS
ORDER BY timestamp DESC;
```

### Query 4: analyze_thesis_change

```sql
-- Track thesis evolution over time
SELECT 
    timestamp,
    transaction_type,
    full_reasoning,
    (sequential action count) as iteration
FROM trading.account_transactions
WHERE symbol = $1
ORDER BY timestamp ASC;  -- Earliest first
```

---

## 6. Implementation Phases

### Phase 1: Create memory_tools.py (1-2 hours)

- [ ] Create file with 4 functions
- [ ] Implement SQL queries
- [ ] Format return strings
- [ ] Add logging/error handling

### Phase 2: Integrate into simple_trader.py (1 hour)

- [ ] Import memory tools
- [ ] Add to agent's available tools
- [ ] Update agent instructions
- [ ] Test tool presence

### Phase 3: Local Testing (1-2 hours)

- [ ] Run trading_system.py locally
- [ ] Trigger agent reasoning
- [ ] Verify memory tool calls happen
- [ ] Check returned data is accurate
- [ ] Check agent uses memory in decisions

### Phase 4: Production Deployment (1 hour)

- [ ] Push code to production
- [ ] Restart agents pod
- [ ] Verify tools are available
- [ ] Monitor logs for tool calls

### Phase 5: Verification & Documentation (1 hour)

- [ ] Run full trading cycle
- [ ] Query PostgreSQL for memory tool results
- [ ] Document examples of agent using memory
- [ ] Create usage guide

---

## 7. Testing Strategy

### Unit Tests (Local)

```python
# Test query returns correct format
test_get_prior_research_returns_string()

# Test conviction level logic
test_get_conviction_level_high()
test_get_conviction_level_medium()
test_get_conviction_level_low()

# Test recent decisions format
test_get_recent_decisions_filters_by_days()

# Test thesis evolution ordering
test_analyze_thesis_change_chronological()
```

### Integration Tests (Local)

```python
# Test agent can access tools
test_agent_has_memory_tools()

# Test agent calls memory during reasoning
test_agent_calls_get_prior_research()

# Test agent uses returned data
test_agent_incorporates_memory_in_decision()

# Test full cycle with memory
test_full_trading_cycle_with_memory()
```

### Production Tests (Kubernetes)

```bash
# After deployment:
1. Run one trading cycle
2. Check logs for memory tool calls
3. Query PostgreSQL for populated transactions
4. Verify agent decisions reference past trades
5. Check no errors in agent logs
```

---

## 8. Success Criteria

✅ **Completion Criteria**:
- [ ] All 4 memory tools implemented
- [ ] Integrated into agent tools
- [ ] Local tests passing
- [ ] Deployed to production
- [ ] At least 1 trading cycle completed with memory tool usage
- [ ] Agent shows reasoning that references past decisions

✅ **Performance Criteria**:
- [ ] Memory tool queries < 100ms
- [ ] No errors in agent logs
- [ ] Agent doesn't spam memory tool calls (reasonable usage)
- [ ] PostgreSQL queries are indexed appropriately

✅ **Functional Criteria**:
- [ ] Agent can retrieve prior research
- [ ] Agent can check conviction levels
- [ ] Agent can see recent decisions
- [ ] Agent can analyze thesis changes
- [ ] Agent uses this info in reasoning

---

## 9. Risk Mitigation

### Risk 1: Agent gets confused with memory tools

**Mitigation**: 
- Clear tool descriptions
- Examples in agent instructions
- Keep tool names simple

### Risk 2: Memory queries are slow

**Mitigation**:
- Add indexes on `symbol`, `account_id`, `timestamp`
- Cache recent decisions if needed
- Limit query results (LIMIT 10)

### Risk 3: Agent misuses memory tools (spams them)

**Mitigation**:
- Rate limiting at agent level
- Monitor logs for over-usage
- Can disable tools if problematic

### Risk 4: Query results are confusing to agent

**Mitigation**:
- Format results clearly
- Include context (prices, dates)
- Use natural language in formatting

---

## 10. Future Enhancements

### Phase 2 (If Useful): Semantic Memory

Only if agent shows need:
```
- Add vector embeddings for full_reasoning
- Query: "Find trades with similar market conditions"
- Only implement if ROI > 10% improvement
```

### Phase 2 (If Needed): Memory Summarization

Compress long histories:
```
- Summarize old trades (> 30 days)
- Keep recent trades detailed
- Keep summaries queryable
```

### Phase 2 (If Requested): Cross-Agent Memory

Share learnings:
```
- "What have other agents done with NVDA?"
- "How does George handle momentum trades?"
- Only if collaboration is desired
```

---

## 11. Documentation Needed

- [ ] Tool function docstrings (code comments)
- [ ] Agent instruction examples
- [ ] SQL query explanations
- [ ] Usage examples (how agent should use)
- [ ] Troubleshooting guide

---

## Decision Points

**Decision 1: Return Format**
- Option A: Natural language strings (agent-friendly)
- Option B: JSON objects (machine-friendly)
- Recommendation: **Option A** (natural language)

**Decision 2: Query Scope**
- Option A: All trades for symbol (unlimited)
- Option B: Limited to recent trades (LIMIT 10)
- Recommendation: **Option B** (efficiency)

**Decision 3: Conviction Level Calculation**
- Option A: Based on buy count only
- Option B: Based on buy/sell ratio
- Option C: Based on time holdings (weighted)
- Recommendation: **Option A** (simplest, works for now)

---

## Timeline Estimate

| Phase | Task | Time | Status |
|-------|------|------|--------|
| 1 | Create memory_tools.py | 1-2h | Pending |
| 2 | Integrate into simple_trader.py | 1h | Pending |
| 3 | Local testing | 1-2h | Pending |
| 4 | Production deployment | 1h | Pending |
| 5 | Verification & docs | 1h | Pending |
| | **TOTAL** | **5-7h** | |

---

## Approval Checkpoints

Before starting each phase:
- [ ] Stakeholder approval of approach
- [ ] Design review complete
- [ ] Success criteria confirmed





















