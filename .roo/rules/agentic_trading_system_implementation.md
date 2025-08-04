# Agentic Trading System Implementation Rule

## Core Principles

### 1. Implementation Plan Adherence
All work MUST follow [`agentic-trading-system/docs/IMPLEMENTATION_PLAN.md`](agentic-trading-system/docs/IMPLEMENTATION_PLAN.md).

**Requirements:**
- Follow 5-phase implementation structure
- Respect phase dependencies and sequencing
- **UPDATE implementation plan status when completing tasks** (mark with ✅)
- Reference specific phase and task numbers

### 2. Source Project Compatibility
Replicated functionality MUST match [`agents/6_mcp`](agents/6_mcp) exactly.

**Requirements:**
- Replicate behavior identically from source
- Use identical MCP server parameters and setup
- Match agent prompts and instructions exactly
- Follow exact LibSQL memory implementation
- Maintain identical autonomous trading behavior

### 3. Enhancement Strategy
**"Replicate Core + Extend"** approach:

**REPLICATED** (Must Match Source):
- 4 Autonomous Trading Agents (Warren, George, Ray, Cathie)
- Researcher Agent with web search and memory
- Memory/Knowledge Graph System (LibSQL)
- Push Notification System (Pushover)
- Trading Floor Orchestration

**ENHANCED** (New Capabilities):
- Java Spring Boot Backend APIs
- React Frontend Dashboard
- Real-time Data Feeds
- Advanced Analytics and Risk Management
- Compliance and Audit Trail
- Backtesting Platform

## Implementation Rules

### Rule 1: Phase-Based Development
**Before any implementation:**
1. Check current phase and task status in implementation plan
2. Ensure prerequisite phases/tasks are complete
3. Follow task sequence specified in plan
4. **Mark tasks as ✅ COMPLETED in implementation plan when finished**

### Rule 2: Source Project Comparison
**For replicated functionality:**
1. Study exact implementation in `agents/6_mcp`
2. Replicate behavior, configuration, and patterns identically
3. Verify implementation works the same way
4. Document any necessary differences

### Rule 3: Enhancement Integration
**For new enhancements:**
1. Never break existing replicated functionality
2. Integrate with Java backend and React frontend
3. Ensure core agents still work identically
4. Document what's new vs. replicated

## File Organization

### Core Agent Files (Must Match Source)
```
agentic-trading-system/agents/
├── mcp_params.py           # MUST match agents/6_mcp/mcp_params.py
├── researcher.py           # MUST match agents/6_mcp/templates.py researcher pattern
├── warren_agent.py         # MUST match agents/6_mcp/traders.py + reset.py Warren
├── george_agent.py         # MUST match agents/6_mcp/traders.py + reset.py George
├── ray_agent.py           # MUST match agents/6_mcp/traders.py + reset.py Ray
├── cathie_agent.py        # MUST match agents/6_mcp/traders.py + reset.py Cathie
└── trading_system.py      # MUST match agents/6_mcp/trading_floor.py behavior
```

### Enhancement Files (New Capabilities)
```
agentic-trading-system/
├── backend/               # NEW: Java Spring Boot APIs
├── frontend/              # NEW: React Dashboard
├── mcp-servers/          # ENHANCED: Python MCP servers with Java integration
└── docs/                 # ENHANCED: Implementation plan and documentation
```

## Validation Checklist

### Before Implementation
- [ ] Current phase identified from implementation plan
- [ ] Prerequisites completed and verified
- [ ] Source project behavior analyzed (if replicating)
- [ ] Enhancement approach defined (if extending)

### After Implementation
- [ ] **Implementation plan status updated with ✅ COMPLETED**
- [ ] Functionality verified against source project
- [ ] Integration tested with existing components
- [ ] Documentation updated

## Quality Gates
1. **Phase Gate**: Cannot proceed to next phase without completing current phase
2. **Source Gate**: Replicated functionality must match source behavior exactly
3. **Integration Gate**: Enhancements must not break core functionality
4. **Documentation Gate**: All changes must be documented in implementation plan

## Usage Example

### ✅ Correct Implementation Approach
```markdown
## Implementing Phase 2.2: Push Notification MCP Server

### Source Analysis
- Analyzed agents/6_mcp/push_server.py
- Identified Pushover integration pattern

### Implementation
- Replicated push_server.py exactly from source
- Added to trader_mcp_server_params following source pattern
- Enhanced with better error handling

### Status Update in Implementation Plan
- Updated docs/IMPLEMENTATION_PLAN.md line 75:
- Changed: "#### 2.2 Push Notification MCP Server (2-3 days)"
- To: "#### ✅ 2.2 Push Notification MCP Server (2-3 days) - **COMPLETED**"
- Added status description with implementation details
```

## Priority and Enforcement

**Priority**: **CRITICAL** - Takes precedence over other implementation preferences

**Scope**: All work in `agentic-trading-system/` project

This rule ensures the project maintains proven autonomous trading capabilities from the source project while systematically adding enterprise-grade enhancements according to the structured implementation plan.