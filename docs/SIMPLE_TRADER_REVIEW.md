# simple_trader.py Code Review - Obsolete Instructions & Code

**Review Date**: 2025-12-18

## Critical Issues Found

### 1. DUPLICATE Researcher Creation (CRITICAL)

**Problem**: `simple_trader.py` has its own `get_researcher_tool()` method (lines 275-337) that creates a researcher with OUTDATED instructions. The orchestrator just implemented a NEW `researcher.py` with database tools, but `simple_trader.py` is NOT using it.

**Current (WRONG)**:
```python
# simple_trader.py line 275
async def get_researcher_tool(self, researcher_mcp_servers) -> Tool:
    """Create researcher tool from external MCP servers"""
    researcher_instructions = f"""You are a financial researcher...
    Make use of your knowledge graph tools...  # ❌ OBSOLETE
    """
    researcher = Agent(
        name="Researcher",
        instructions=researcher_instructions,  # ❌ OLD instructions
        model=self.model_name,
        mcp_servers=researcher_mcp_servers,
    )
    return researcher.as_tool(...)
```

**Should be**:
```python
# simple_trader.py line 82 (in ToolFactory.create_agent)
from researcher import get_researcher_tool

researcher_tool = await get_researcher_tool(
    self.researcher_mcp_servers,
    self.trader.model_name
)
```

**Impact**:
- ❌ Researcher does NOT have database query tools
- ❌ Researcher has outdated knowledge graph instructions
- ❌ Two conflicting implementations exist

**Fix**: Remove lines 275-337 from `simple_trader.py` and import from `researcher.py`

---

### 2. Obsolete Knowledge Graph References (OBSOLETE)

**Lines 288-295**: Instructions reference "knowledge graph tools" that don't exist:

```python
"""
Important: making use of your knowledge graph to retrieve and store information...

Make use of your knowledge graph tools to store and recall entity information...
"""
```

**Status**: ❌ OBSOLETE - Memory MCP was removed in November 2025 (commit 2901d70)

**Impact**: Confusing instructions that reference non-existent tools

**Fix**: Already fixed in NEW `researcher.py`, but need to use that instead

---

### 3. Trading Agent Instructions Review

**Lines 389-396**: Instructions say "YOU MUST CALL query_trading_history"

```python
"""
1. **Historical Context - MANDATORY FIRST STEP**:
   - **YOU MUST CALL query_trading_history(symbol, days) for ANY stock you're considering**
"""
```

**Status**: ✅ STILL VALID - Trading agents should query their own history

**Rationale**:
- Trading agent queries its own past decisions
- Researcher queries to understand agent context (different use case)
- Both can coexist

**No change needed**

---

### 4. Account Data Handling

**Line 456**: "Account snapshot is provided in the prompt; do not query balance/holdings via tools"

```python
"""
You have access to end-of-day market data from Polygon.io (previous trading day close).
Account snapshot is provided in the prompt; do not query balance/holdings via tools.
"""
```

**Status**: ✅ CORRECT - We pre-fetch balance/holdings in Phase 1

**Rationale**: Avoid unnecessary tool calls, data is in message

**No change needed**

---

### 5. Researcher Tool Usage Instructions

**Lines 349-386**: NEW mandatory research instructions added

**Status**: ✅ GOOD - Comprehensive examples of multiple research calls

**Examples include**:
- Portfolio review
- Opportunity search
- Sector analysis
- Stock deep dive

**No issues found**

---

## Summary of Required Changes

### Change 1: Remove Obsolete Researcher Method ✅ REQUIRED

**File**: `simple_trader.py`

**Remove**: Lines 275-337 (entire `get_researcher_tool` method)

**Replace with** (in `ToolFactory.create_agent`, line 80-83):
```python
# Import at top of file
from researcher import get_researcher_tool

# In ToolFactory.create_agent method
researcher_tool = await get_researcher_tool(
    self.researcher_mcp_servers,
    self.trader.model_name
)
```

---

### Change 2: Verify Imports

Ensure these imports exist at top of `simple_trader.py`:
```python
from researcher import get_researcher_tool  # ADD THIS
```

Remove this import (no longer used):
```python
from mcp_params import researcher_mcp_server_params  # ← Still needed for MCP servers list
```

---

## Files Status

| File | Status | Action Needed |
|------|--------|---------------|
| `simple_trader.py` | ❌ OUT OF SYNC | Remove duplicate researcher method |
| `researcher.py` | ✅ CURRENT | No changes |
| `agent_executor.py` | ✅ CURRENT | No changes |
| `tool_tracking.py` | ✅ CURRENT | No changes |

---

## Testing After Fix

1. **Verify researcher has database tools**:
   - Run agent cycle
   - Check logs for `query_holdings_tool` calls by Researcher

2. **Verify instructions are current**:
   - No references to "knowledge graph" in Researcher output
   - Researcher mentions "database tools" in reasoning

3. **Verify mandatory research works**:
   - Agent gets error if skipping research
   - Error message matches new enforcement code

---

## Next Steps

1. ✅ Fix: Remove duplicate `get_researcher_tool()` from `simple_trader.py`
2. ✅ Import: Use `get_researcher_tool()` from `researcher.py`
3. ✅ Test: Run agent cycle to verify database tools work
4. ✅ Deploy: Deploy to staging for live testing
