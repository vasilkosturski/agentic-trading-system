# Agentic Trading System - Implementation Plan
*Based on agents/6_mcp Source Project Analysis*

## Executive Summary

This implementation plan focuses on integrating the missing components from the [`agents/6_mcp`](../../../agents/6_mcp) source project into our existing Java Spring Boot backend and React frontend architecture. We have identified 7 critical components that need to be implemented to complete our agentic trading system.

## Architecture Overview

Our system combines the proven components from the source project with our enhanced architecture:

- **Backend**: Java Spring Boot (existing) + Python MCP servers (from source)
- **Frontend**: React (existing) + Gradio dashboard (from source) for monitoring
- **Database**: H2/JPA (existing) + SQLite (source) + LibSQL memory (source)
- **Agents**: Python-based with MCP integration (from source)

## Missing Components from Source

### 1. LibSQL Memory System 🧠
**Source**: [`mcp_params.py:41-45`](../../../agents/6_mcp/mcp_params.py:41)
```python
{
    "command": "npx",
    "args": ["-y", "mcp-memory-libsql"],
    "env": {"LIBSQL_URL": f"file:./memory/{name}.db"},
}
```
**Purpose**: Persistent knowledge graph for each trader to store and recall information about companies, market conditions, and trading decisions.

### 2. Web Fetching MCP Server 🌐
**Source**: [`mcp_params.py:35`](../../../agents/6_mcp/mcp_params.py:35)
```python
{"command": "uvx", "args": ["mcp-server-fetch"]}
```
**Purpose**: Comprehensive web scraping capabilities for additional research beyond news search.

### 3. Brave Search Integration 🔍
**Source**: [`mcp_params.py:36-40`](../../../agents/6_mcp/mcp_params.py:36)
```python
{
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
    "env": {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")},
}
```
**Purpose**: Real-time financial news research for informed trading decisions.

### 4. Push Notifications 📱
**Source**: [`push_server.py:22-27`](../../../agents/6_mcp/push_server.py:22)
- Pushover integration for trade alerts
- Brief portfolio health summaries
- Real-time notification system

### 5. Alternating Trade/Rebalance Cycles 🔄
**Source**: [`traders.py:96-100`](../../../agents/6_mcp/traders.py:96) and [`templates.py:50-86`](../../../agents/6_mcp/templates.py:50)
```python
message = (
    trade_message(self.name, strategy, account)
    if self.do_trade
    else rebalance_message(self.name, strategy, account)
)
```
**Purpose**: Systematic alternation between finding new opportunities and rebalancing existing portfolio.

### 6. Market Hours Integration ⏰
**Source**: [`trading_floor.py:45`](../../../agents/6_mcp/trading_floor.py:45)
```python
if RUN_EVEN_WHEN_MARKET_IS_CLOSED or is_market_open():
    await asyncio.gather(*[trader.run() for trader in traders])
```
**Purpose**: Conditional execution based on actual market status.

### 7. Gradio Dashboard 📊
**Source**: [`app.py:1-190`](../../../agents/6_mcp/app.py:1)
- Real-time trading floor visualization
- Portfolio value charts with Plotly
- Holdings and transaction tables
- Live log streaming with color coding
- Multi-trader dashboard view

## 4-Phase Implementation Plan

### Phase 1: MCP Server Integration (Week 1-2)

#### 1.1 LibSQL Memory System
**Priority**: Critical
**Time**: 3-4 days

**Tasks**:
1. Install LibSQL MCP server: `npm install -g mcp-memory-libsql`
2. Create memory directory structure: `mkdir -p agents/memory`
3. Update [`mcp_params.py`](../../../agents/6_mcp/mcp_params.py:33) to include memory server
4. Integrate knowledge graph into researcher agent instructions
5. Test entity storage and retrieval

#### 1.2 Web Fetching & Brave Search
**Priority**: High
**Time**: 3-4 days

**Tasks**:
1. Install MCP servers:
   - `pip install mcp-server-fetch`
   - `npm install -g @modelcontextprotocol/server-brave-search`
2. Configure Brave API key in environment
3. Update researcher MCP server parameters
4. Implement fallback logic: Brave Search → Web Fetch on rate limits
5. Test news research capabilities

#### 1.3 Push Notifications
**Priority**: Medium
**Time**: 2-3 days

**Tasks**:
1. Set up Pushover account and get API keys
2. Configure environment variables: `PUSHOVER_USER`, `PUSHOVER_TOKEN`
3. Implement push notification MCP server
4. Integrate notifications into trader workflow
5. Test alert system

### Phase 2: Trading Logic Enhancement (Week 3)

#### 2.1 Alternating Trade/Rebalance Cycles
**Priority**: High
**Time**: 3-4 days

**Tasks**:
1. Implement cycle toggle logic in trader class
2. Create trade and rebalance message templates
3. Update agent instructions for both modes
4. Test alternating behavior
5. Integrate with Java backend scheduling

#### 2.2 Market Hours Integration
**Priority**: Medium
**Time**: 2-3 days

**Tasks**:
1. Implement market status detection using Polygon API
2. Add conditional execution logic
3. Configure `RUN_EVEN_WHEN_MARKET_IS_CLOSED` environment variable
4. Test market hours scheduling
5. Integrate with Java backend scheduler

### Phase 3: Dashboard Implementation (Week 4)

#### 3.1 Gradio Dashboard
**Priority**: High
**Time**: 4-5 days

**Tasks**:
1. Set up Gradio environment and dependencies
2. Implement trader view components from [`app.py`](../../../agents/6_mcp/app.py:96)
3. Create portfolio value charts with Plotly
4. Implement real-time log streaming
5. Add auto-refresh timers (120s data, 0.5s logs)
6. Test multi-trader dashboard

#### 3.2 React Frontend Integration
**Priority**: Medium
**Time**: 2-3 days

**Tasks**:
1. Add Gradio dashboard link to React navigation
2. Implement WebSocket connection for real-time data
3. Create dashboard iframe integration
4. Test dual-interface functionality

### Phase 4: Integration & Testing (Week 5)

#### 4.1 End-to-End Integration
**Priority**: Critical
**Time**: 3-4 days

**Tasks**:
1. Test complete MCP server orchestration
2. Validate agent workflow with all components
3. Test Java backend ↔ Python agents communication
4. Verify database synchronization
5. Test error handling and recovery

#### 4.2 Performance & Monitoring
**Priority**: High
**Time**: 2-3 days

**Tasks**:
1. Load test with multiple concurrent agents
2. Monitor MCP server performance
3. Implement health checks
4. Add comprehensive logging
5. Test notification system reliability

## Technical Specifications

### MCP Server Configuration
```python
# agents/mcp_params.py
trader_mcp_server_params = [
    {"command": "uv", "args": ["run", "accounts_server.py"]},
    {"command": "uv", "args": ["run", "push_server.py"]},
    market_mcp,  # Polygon or local market server
]

def researcher_mcp_server_params(name: str):
    return [
        {"command": "uvx", "args": ["mcp-server-fetch"]},
        {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")},
        },
        {
            "command": "npx",
            "args": ["-y", "mcp-memory-libsql"],
            "env": {"LIBSQL_URL": f"file:./memory/{name}.db"},
        },
    ]
```

### Environment Variables
```bash
# Required for full functionality
BRAVE_API_KEY=your_brave_api_key
PUSHOVER_USER=your_pushover_user_key
PUSHOVER_TOKEN=your_pushover_app_token
POLYGON_API_KEY=your_polygon_api_key
RUN_EVERY_N_MINUTES=60
RUN_EVEN_WHEN_MARKET_IS_CLOSED=false
```

### Directory Structure
```
agentic-trading-system/
├── agents/
│   ├── memory/           # LibSQL databases per trader
│   ├── mcp_params.py     # MCP server configurations
│   ├── traders.py        # Enhanced trader logic
│   ├── templates.py      # Trade/rebalance templates
│   └── trading_floor.py  # Orchestration with market hours
├── backend/              # Java Spring Boot (existing)
├── frontend/             # React application (existing)
└── monitoring/
    └── gradio_dashboard.py  # Real-time monitoring
```

## Success Metrics

### Technical
- All 7 missing components operational
- <2s latency for portfolio updates
- Persistent knowledge graph per trader
- 99% uptime during market hours

### Business
- Intelligent trading decisions using news research
- Effective portfolio rebalancing cycles
- Timely push notifications for significant changes
- Real-time monitoring capabilities

## Risk Mitigation

### API Rate Limits
- **Mitigation**: Implement caching, request queuing, fallback to fetch server

### MCP Server Stability
- **Mitigation**: Health checks, auto-restart mechanisms, graceful degradation

### Memory System Performance
- **Mitigation**: Efficient indexing, query optimization, periodic cleanup

## Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| **Phase 1** | Week 1-2 | LibSQL Memory, Web Fetch, Brave Search, Push Notifications |
| **Phase 2** | Week 3 | Trade/Rebalance Cycles, Market Hours Integration |
| **Phase 3** | Week 4 | Gradio Dashboard, React Integration |
| **Phase 4** | Week 5 | End-to-End Testing, Performance Optimization |

## Conclusion

This implementation plan integrates the proven components from the agents/6_mcp source project into our existing Java/React architecture. The focus is on the 7 missing components that will complete our agentic trading system while maintaining our enhanced backend and frontend capabilities.

Key success factors:
1. **Prioritize LibSQL memory system** for intelligent agent behavior
2. **Implement robust MCP server integration** for full functionality  
3. **Build dual monitoring interfaces** (Gradio + React)
4. **Ensure system reliability** through comprehensive testing

With proper execution, we will have a fully functional agentic trading system that combines the best of both architectures.