# Researcher Agent Database Enhancement - Implementation Plan

## Executive Summary

Enhance the Researcher agent with database query capabilities to provide context-aware research by combining historical trading data with real-time web search. This enables the Researcher to understand each trading agent's portfolio context, past decisions, and reasoning when conducting market research.

## Current Architecture

### Researcher Agent (researcher.py)
- **Current capabilities**: Web search via Brave Search MCP, web content fetch, knowledge graph storage
- **Limitation**: No access to trading database - cannot see agent holdings, trades, or past decisions
- **Location**: `agentic-trading-system/agents/researcher.py`

### Trading Agents (simple_trader.py)
- **Current capabilities**: Call Researcher tool, query own trading history via memory_tools
- **Usage pattern**: Can call Researcher multiple times per cycle with different research requests
- **Location**: `agentic-trading-system/agents/simple_trader.py`

### Agent Executor (agent_executor.py)
- **Phase 5**: Parses agent results and tracks tool usage
- **Current tracking**: Logs Researcher queries and sources, but not designed for multiple calls
- **Location**: `agentic-trading-system/agents/agent_executor.py`

### Database Schema
**Relevant tables**:
- `trading.holdings` - Current positions (symbol, quantity, averagePrice)
- `trading.account_transactions` - Trade history (BUY/SELL transactions with timestamps)
- `analytics.agent_runs` - Past decisions with full_reasoning, research_sources, historical_context

## Implementation Plan

### 1. Add Database Query Tools to Researcher

**File**: `agentic-trading-system/agents/researcher.py`

**New Tools** (following existing patterns from memory_tools.py):

```python
async def query_agent_holdings(agent_name: str) -> str:
    """Get current holdings and positions for an agent.

    Returns JSON with:
    - holdings: List of {symbol, quantity, averagePrice, currentValue}
    - totalValue: Total portfolio value
    - cash: Available cash
    """
    # Call: GET /api/memory/holdings?agentName={agent_name}
    # Returns: JSON string
```

```python
async def query_trade_history(
    agent_name: str,
    symbol: Optional[str] = None,
    days: int = 30
) -> str:
    """Get trade history for an agent.

    Args:
        agent_name: Agent name (Warren, George, Ray, Cathie)
        symbol: Optional - filter by stock symbol
        days: How many days back to look

    Returns JSON with:
    - trades: List of {date, action, symbol, quantity, price, reasoning}
    """
    # If symbol provided: Call existing /api/memory/trading-history
    # If symbol is None: Call /api/memory/all-trades (NEW endpoint)
```

```python
async def query_past_decisions(
    agent_name: str,
    symbol: Optional[str] = None,
    days: int = 30
) -> str:
    """Get past decisions (including HOLD) with full reasoning.

    Args:
        agent_name: Agent name
        symbol: Optional - filter by stock symbol
        days: How many days back to look

    Returns JSON with:
    - decisions: List of {date, action, symbol, rationale, fullReasoning}
    - Includes HOLD decisions and research sources
    """
    # Call: GET /api/memory/decisions?agentName={}&symbol={}&days={}
```

```python
async def lookup_price(symbol: str) -> str:
    """Get current market price for a stock.

    Returns JSON with:
    - symbol: Stock symbol
    - price: Current price
    - timestamp: Price timestamp
    """
    # Reuse existing market_tools.lookup_share_price
    # Wrap in JSON format for consistency
```

**Integration approach**:
- Use same HTTP client pattern as `memory_tools.py` and `trading_tools.py`
- Call backend endpoints via `call_backend()` from `http_client.py`
- Return JSON strings (same format as memory_tools)
- Add tools to `get_researcher()` function as function_tools

### 2. Update Researcher Instructions

**File**: `agentic-trading-system/agents/researcher.py`

**New instruction sections**:

```python
instructions = f"""You are a financial researcher with access to:

1. **Database Tools** (understand agent context):
   - query_agent_holdings(agent_name) - See what they currently own
   - query_trade_history(agent_name, symbol, days) - See their trade history
   - query_past_decisions(agent_name, symbol, days) - See past decisions with reasoning
   - lookup_price(symbol) - Get current market price

2. **Web Research Tools** (gather current information):
   - Brave Search - Search for news, analysis, market data
   - Web fetch - Retrieve specific URLs
   - Knowledge graph - Store/recall company information

**RESEARCH WORKFLOW**:

When conducting research for a trading agent:
1. **Understand Context First** (if agent_name provided):
   - Query their holdings to see current positions
   - Review trade history for relevant stocks
   - Check past decisions to understand their thesis

2. **Combine Historical + Current**:
   - Use database to understand WHAT they hold and WHY
   - Use web search to find CURRENT news and conditions
   - Synthesize both into context-aware research

3. **Return JSON Response** (MANDATORY):
   {{
     "summary": "Research findings that reference both historical context and current news",
     "sources": [
       {{"title": "Article Title", "url": "https://..."}}
     ],
     "context": {{
       "agent_holdings": [...],  // If queried
       "relevant_history": [...]  // If queried
     }}
   }}

**EXAMPLE RESEARCH FLOW**:

Request: "Research NVDA for Warren"
1. query_agent_holdings("Warren") -> See if Warren owns NVDA
2. query_past_decisions("Warren", "NVDA", 30) -> Understand Warren's thesis
3. Brave Search: "NVDA latest news earnings AI" -> Get current info
4. Synthesize: "Warren currently holds 150 NVDA (bought at $145 for AI growth thesis).
   Recent earnings beat expectations (TechCrunch), AI demand surging (Reuters).
   Thesis remains valid."

The current datetime is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
```

### 3. Update Trading Agent Instructions

**File**: `agentic-trading-system/agents/simple_trader.py`

**Update `get_trader_instructions()` method** - Add guidance for Researcher usage:

```python
def get_trader_instructions(self) -> str:
    # ... existing instructions ...

    # ADD THIS SECTION:
    """
    **USING THE RESEARCHER TOOL**:

    You can call Researcher MULTIPLE TIMES per cycle for different purposes:

    1. **Portfolio Review**: "Review my current holdings and find news on each position"
    2. **Opportunity Search**: "Find growth stocks in the AI sector that fit my strategy"
    3. **Sector Analysis**: "Analyze technology sector outlook and risks"
    4. **Stock Deep Dive**: "Research NVDA earnings, outlook, and competitive position"

    **ENRICHING RESEARCH REQUESTS**:

    When calling Researcher, provide context about what you're looking for:

    ❌ Bad: researcher("research stocks")
    ✅ Good: researcher("I'm Warren focusing on value. Review my holdings and find undervalued opportunities in tech")

    ❌ Bad: researcher("what about NVDA")
    ✅ Good: researcher("I hold 150 NVDA bought at $145 for AI thesis. Check latest earnings and sentiment")

    The Researcher has access to your portfolio and history - it will automatically query
    your holdings and past decisions to provide context-aware research.

    **MULTIPLE CALLS**:

    Example cycle:
    1. researcher("Review my holdings - any red flags?")
    2. researcher("Find 2-3 new opportunities in healthcare sector")
    3. researcher("Deep dive on AAPL - considering selling")

    Each call is tracked and sources are saved for transparency.
    """
```

### 4. Track Multiple Research Calls

**File**: `agentic-trading-system/agents/agent_executor.py`

**Update `_phase5_parse_results()` method**:

```python
async def _phase5_parse_results(self, result) -> None:
    """Phase 5: Parse agent output and track tool usage."""

    research_call_count = 0
    research_calls = []  # Track each research call separately

    # ... existing parsing logic ...

    # In Researcher tool handling section:
    if tool_name == "Researcher":
        research_call_count += 1
        research_conducted = True

        # Extract query and sources
        query = self._extract_researcher_query(items, i)
        sources = self._extract_sources_from_output(tool_result_full)
        result_summary = self._parse_research_summary(tool_result_full, sources)

        # Track this specific research call
        research_calls.append({
            "call_number": research_call_count,
            "query": query,
            "summary": result_summary,
            "sources_found": len(sources),
            "sources": sources[:5]  # Store first 5 sources
        })

        # Log individual research call
        logger.info(f"  📎 Research call #{research_call_count}: {query[:50]}... ({len(sources)} sources)")

        if self.tracker:
            self.tracker.log_research_query(
                f"[Call {research_call_count}] {query}",
                result_summary,
                sources
            )

    # After loop, log summary
    if research_call_count > 0:
        logger.info(f"📊 Total research calls: {research_call_count}")
        if self.tracker:
            self.tracker.log_reasoning(
                "research",
                f"Research completed ({research_call_count} queries)",
                f"Conducted {research_call_count} research queries. Details: {json.dumps(research_calls, indent=2)}"
            )
```

**Add helper methods**:

```python
def _extract_researcher_query(self, items: list, current_index: int) -> str:
    """Extract the original query/request sent to Researcher tool."""
    # Look back in items to find tool_call with Researcher + arguments
    # Parse arguments to get the query/request/message parameter
    # Return query string
```

## Backend Changes Required

### New API Endpoints

**1. GET /api/memory/holdings**
- Parameters: `agentName`
- Returns: Current holdings with values

**2. GET /api/memory/all-trades**
- Parameters: `agentName`, `days`
- Returns: All trades (not filtered by symbol)

**3. GET /api/memory/decisions**
- Parameters: `agentName`, `symbol` (optional), `days`
- Returns: All decisions including HOLD with full reasoning

## Implementation Sequence

1. **Backend first** (if endpoints don't exist):
   - Add missing endpoints to MemoryController.java
   - Test endpoints via curl/Postman

2. **Researcher tools**:
   - Add database query functions to researcher.py
   - Update instructions
   - Test in isolation

3. **Trading agent instructions**:
   - Update simple_trader.py instructions
   - Add Researcher usage examples

4. **Executor tracking**:
   - Update agent_executor.py Phase 5
   - Test with multiple Researcher calls

5. **Integration testing**:
   - Run full trading cycle
   - Verify Researcher calls are tracked
   - Check logged sources and queries

## Expected Behavior After Implementation

### Example Research Cycle

**Trading Agent (Warren)**:
```
Cycle starts -> Calls Researcher 3 times:
1. "Review my holdings and check for news on each position"
2. "Find undervalued opportunities in the financial sector"
3. "Deep dive on JPM - considering adding to position"
```

**Researcher Tool**:
```
Call 1:
- query_agent_holdings("Warren") -> Sees 8 positions
- query_past_decisions("Warren", days=7) -> Recent activity
- Brave Search for each holding -> Latest news
- Returns: Synthesis of holdings + current news

Call 2:
- Brave Search: "undervalued financial stocks"
- lookup_price for each candidate
- Returns: List of opportunities with rationale

Call 3:
- query_trade_history("Warren", "JPM", 30) -> Warren's JPM history
- query_past_decisions("Warren", "JPM", 30) -> Past JPM reasoning
- Brave Search: "JPM latest earnings outlook"
- Returns: Context-aware analysis referencing history + current
```

**Agent Executor Tracking**:
```
Phase 5 logs:
- 🔧 Tool call: Researcher (call #1)
  📎 Research: 8 sources, query: "Review my holdings..."
- 🔧 Tool call: Researcher (call #2)
  📎 Research: 5 sources, query: "Find undervalued opportunities..."
- 🔧 Tool call: Researcher (call #3)
  📎 Research: 6 sources, query: "Deep dive on JPM..."

📊 Total research calls: 3
```

## Files to Modify Summary

| File | Changes | Lines Est. |
|------|---------|-----------|
| `researcher.py` | Add 4 DB query tools + update instructions | +150 |
| `simple_trader.py` | Update instructions with Researcher guidance | +40 |
| `agent_executor.py` | Track multiple research calls in Phase 5 | +60 |
| Backend (Java) | Add missing endpoints (if needed) | +200 |

## Testing Strategy

1. **Unit tests**:
   - Test each DB query tool independently
   - Verify JSON parsing and error handling

2. **Integration tests**:
   - Run Researcher with mock agent_name
   - Verify it queries holdings + history + web search
   - Check JSON response format

3. **Full cycle tests**:
   - Run trading agent with multiple Researcher calls
   - Verify all calls are tracked
   - Check logs show query + source count

4. **Edge cases**:
   - Agent with no holdings
   - Symbol with no trade history
   - Multiple Researcher calls in same cycle

## Rollback Plan

If issues arise:
1. **Researcher tools**: Comment out new DB query tools (web search still works)
2. **Instructions**: Revert to previous instructions (agents still functional)
3. **Tracking**: Revert executor changes (basic tracking still works)

No database schema changes required - uses existing tables.

## Success Criteria

- ✅ Researcher can query agent holdings, trades, decisions
- ✅ Researcher combines DB queries with web search in responses
- ✅ Trading agents can call Researcher multiple times per cycle
- ✅ Agent executor logs each research call with query + sources
- ✅ All research sources tracked for transparency
- ✅ No breaking changes to existing functionality

## Timeline Estimate

- Backend endpoints (if needed): 2-3 hours
- Researcher enhancements: 2-3 hours
- Trading agent instructions: 1 hour
- Executor tracking: 1-2 hours
- Testing: 2-3 hours

**Total**: 8-12 hours implementation + testing
