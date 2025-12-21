#!/usr/bin/env python3
"""
Researcher Agent - Financial research with database and web capabilities.

Structure:
- get_researcher_instructions() → System prompt
- build_research_message(query) → Invocation context
- create_researcher_agent(...) → Create agent instance
- run_researcher(query, ...) → Execute and return response

To use as a tool from another agent:
    researcher = await create_researcher_agent(mcp_servers, model)
    tool = researcher.as_tool(tool_name="Researcher", tool_description="...")
"""

from agents import Agent, Runner, function_tool
from datetime import datetime
from typing import Any
import json
from config import BACKEND_BASE_URL
from http_client import call_backend, BackendAPIError


# ============================================================================
# Database query functions (tools for the researcher)
# ============================================================================

async def query_agent_holdings(agent_name: str) -> str:
    """Get current holdings and positions for a trading agent.

    Args:
        agent_name: Agent name (Warren, George, Ray, Cathie)

    Returns:
        JSON string with holdings, balance, and position count
    """
    try:
        url = f"{BACKEND_BASE_URL}/api/memory/holdings"
        params = {"agentName": agent_name}
        response = await call_backend("GET", url, params=params, timeout=10)
        return response.text
    except BackendAPIError as e:
        if e.status_code == 404:
            return json.dumps({"error": "Agent not found", "holdings": []})
        return json.dumps({"error": str(e), "holdings": []})


async def query_recent_activity(agent_name: str, days: int = 30) -> str:
    """Get recent trading activity across ALL stocks for an agent.

    Args:
        agent_name: Agent name (Warren, George, Ray, Cathie)
        days: How many days back to look (default 30)

    Returns:
        JSON string with recent activity (trades, decisions, reasoning)
    """
    try:
        url = f"{BACKEND_BASE_URL}/api/memory/recent-activity"
        params = {"agentName": agent_name, "days": days}
        response = await call_backend("GET", url, params=params, timeout=10)
        return response.text
    except BackendAPIError as e:
        if e.status_code == 404:
            return json.dumps({"error": "No recent activity found"})
        return json.dumps({"error": str(e)})


async def query_symbol_history(agent_name: str, symbol: str, days: int = 30) -> str:
    """Get trading history for a SPECIFIC stock.

    Args:
        agent_name: Agent name (Warren, George, Ray, Cathie)
        symbol: Stock symbol to look up (e.g., AAPL, NVDA)
        days: How many days back to look (default 30)

    Returns:
        JSON string with trading history for this symbol
    """
    try:
        url = f"{BACKEND_BASE_URL}/api/memory/trading-history"
        params = {"agentName": agent_name, "symbol": symbol, "days": days}
        response = await call_backend("GET", url, params=params, timeout=10)
        return response.text
    except BackendAPIError as e:
        if e.status_code == 404:
            return json.dumps({"error": f"No history found for {symbol}"})
        return json.dumps({"error": str(e)})


async def lookup_price_json(symbol: str) -> str:
    """Get current market price for a stock (JSON format).

    Args:
        symbol: Stock symbol (e.g., AAPL, NVDA)

    Returns:
        JSON string with symbol, price, timestamp
    """
    from market_tools import lookup_share_price
    try:
        price = await lookup_share_price(symbol)
        return json.dumps({
            "symbol": symbol,
            "price": price,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return json.dumps({"error": str(e), "symbol": symbol})


# ============================================================================
# Agent structure (matches simple_trader.py pattern)
# ============================================================================

def get_researcher_instructions() -> str:
    """Get researcher system prompt - defines identity, tools, and rules.
    
    Returns:
        System prompt for the researcher agent
    """
    return """You are a financial researcher with access to both historical data and current market information.

**DATABASE TOOLS** (understand agent context):
- query_holdings_tool(agent_name) - See what the agent currently owns
- query_recent_activity_tool(agent_name, days) - Recent activity across ALL stocks
- query_symbol_history_tool(agent_name, symbol, days) - History for a SPECIFIC stock
- lookup_price_tool(symbol) - Get current market price

**WEB RESEARCH TOOLS** (gather current information):
- Brave Search - Search for news, analysis, market data
- Web fetch - Retrieve specific URLs
- Knowledge graph - Store/recall company information

**RESEARCH WORKFLOW**:

When conducting research (if agent_name is mentioned in the request):
1. **Understand Context First**:
   - Query their holdings to see current positions
   - Use query_recent_activity_tool for general overview
   - Use query_symbol_history_tool for specific stock details

2. **Combine Historical + Current**:
   - Use database to understand WHAT they hold and WHY
   - Use web search to find CURRENT news and market conditions
   - Synthesize both into context-aware research

3. **Return JSON Response** (MANDATORY):
   {
     "summary": "Research findings referencing both historical context and current news",
     "sources": [
       {"title": "Article Title", "url": "https://..."}
     ]
   }

**IMPORTANT**:
- Use your knowledge graph to store and recall entity information
- ALWAYS include at least 2-3 sources with actual URLs from your searches
- DO NOT make up or hallucinate URLs
"""


def build_research_message(query: str) -> str:
    """Build user message for this research request.
    
    Args:
        query: The research query/request
        
    Returns:
        User message for this invocation
    """
    return f"""Current time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Research request: {query}

Conduct your research and return a JSON response with summary and sources.
"""


async def create_researcher_agent(mcp_servers, model_name: str) -> Agent:
    """Create researcher agent with all tools.
    
    Args:
        mcp_servers: MCP servers for web research (Brave, etc.)
        model_name: Model to use
        
    Returns:
        Agent instance ready to run
    """
    # Wrap database functions as tools
    @function_tool
    async def query_holdings_tool(agent_name: str) -> str:
        """Get current holdings for a trading agent"""
        return await query_agent_holdings(agent_name)

    @function_tool
    async def query_recent_activity_tool(agent_name: str, days: int = 30) -> str:
        """Get recent activity across ALL stocks for an agent"""
        return await query_recent_activity(agent_name, days)

    @function_tool
    async def query_symbol_history_tool(agent_name: str, symbol: str, days: int = 30) -> str:
        """Get trading history for a SPECIFIC stock"""
        return await query_symbol_history(agent_name, symbol, days)

    @function_tool
    async def lookup_price_tool(symbol: str) -> str:
        """Get current market price for a stock"""
        return await lookup_price_json(symbol)

    db_tools = [
        query_holdings_tool,
        query_recent_activity_tool,
        query_symbol_history_tool,
        lookup_price_tool,
    ]

    return Agent[Any](
        name="Researcher",
        instructions=get_researcher_instructions(),
        model=model_name,
        mcp_servers=mcp_servers,
        tools=db_tools,
    )


async def run_researcher(
    query: str,
    mcp_servers,
    model_name: str = "gpt-4o-mini"
) -> str:
    """Run researcher agent independently and return response.
    
    This is the main entry point for standalone use or testing.
    
    Args:
        query: Research request
        mcp_servers: MCP servers for web research
        model_name: Model to use
        
    Returns:
        Research response (JSON string with summary and sources)
    """
    agent = await create_researcher_agent(mcp_servers, model_name)
    message = build_research_message(query)
    
    result = await Runner.run(agent, message)
    
    # Extract final response
    if result and hasattr(result, 'final_output'):
        return result.final_output
    return json.dumps({"error": "No response from researcher"})


