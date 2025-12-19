#!/usr/bin/env python3

from agents import Agent, Tool, function_tool
from datetime import datetime
from typing import Optional
import json
from base_agent import get_model
from config import BACKEND_BASE_URL
from http_client import call_backend, BackendAPIError


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


async def query_trade_history(
    agent_name: str,
    symbol: Optional[str] = None,
    days: int = 30
) -> str:
    """Get trade history for a trading agent.

    Args:
        agent_name: Agent name (Warren, George, Ray, Cathie)
        symbol: Optional stock symbol to filter by
        days: How many days back to look (default 30)

    Returns:
        JSON string with trade history
    """
    try:
        if symbol:
            # Use existing endpoint for specific stock
            url = f"{BACKEND_BASE_URL}/api/memory/trading-history"
            params = {"agentName": agent_name, "symbol": symbol, "days": days}
        else:
            # Use recent activity for all trades
            url = f"{BACKEND_BASE_URL}/api/memory/recent-activity"
            params = {"agentName": agent_name, "days": days}

        response = await call_backend("GET", url, params=params, timeout=10)
        return response.text
    except BackendAPIError as e:
        if e.status_code == 404:
            return json.dumps({"error": "No trade history found"})
        return json.dumps({"error": str(e)})


async def query_past_decisions(
    agent_name: str,
    symbol: Optional[str] = None,
    days: int = 30
) -> str:
    """Get past decisions (BUY/SELL/HOLD) with full reasoning.

    This queries agent_runs table which includes:
    - All decisions (BUY, SELL, HOLD)
    - Full reasoning and rationale
    - Research sources used
    - Historical context

    Args:
        agent_name: Agent name (Warren, George, Ray, Cathie)
        symbol: Optional stock symbol to filter by
        days: How many days back to look (default 30)

    Returns:
        JSON string with past decisions and reasoning
    """
    try:
        if symbol:
            # Use trading history which includes run context
            url = f"{BACKEND_BASE_URL}/api/memory/trading-history"
            params = {"agentName": agent_name, "symbol": symbol, "days": days}
        else:
            # Use recent activity which includes all decisions
            url = f"{BACKEND_BASE_URL}/api/memory/recent-activity"
            params = {"agentName": agent_name, "days": days}

        response = await call_backend("GET", url, params=params, timeout=10)
        return response.text
    except BackendAPIError as e:
        if e.status_code == 404:
            return json.dumps({"error": "No past decisions found"})
        return json.dumps({"error": str(e)})


async def lookup_price_json(symbol: str) -> str:
    """Get current market price for a stock (JSON format).

    Wraps market_tools.lookup_share_price in JSON for consistency.

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


async def get_researcher(mcp_servers, model_name) -> Agent:
    """Create researcher agent with database query capabilities"""

    # Wrap async functions as tools
    @function_tool
    async def query_holdings_tool(agent_name: str) -> str:
        """Get current holdings for a trading agent"""
        return await query_agent_holdings(agent_name)

    @function_tool
    async def query_trades_tool(agent_name: str, symbol: str = None, days: int = 30) -> str:
        """Get trade history for a trading agent"""
        return await query_trade_history(agent_name, symbol, days)

    @function_tool
    async def query_decisions_tool(agent_name: str, symbol: str = None, days: int = 30) -> str:
        """Get past decisions with full reasoning"""
        return await query_past_decisions(agent_name, symbol, days)

    @function_tool
    async def lookup_price_tool(symbol: str) -> str:
        """Get current market price for a stock"""
        return await lookup_price_json(symbol)

    instructions = f"""You are a financial researcher with access to both historical data and current market information.

**DATABASE TOOLS** (understand agent context):
- query_holdings_tool(agent_name) - See what the agent currently owns
- query_trades_tool(agent_name, symbol, days) - See their trade history
- query_decisions_tool(agent_name, symbol, days) - See past decisions with full reasoning
- lookup_price_tool(symbol) - Get current market price

**WEB RESEARCH TOOLS** (gather current information):
- Brave Search - Search for news, analysis, market data
- Web fetch - Retrieve specific URLs
- Knowledge graph - Store/recall company information

**RESEARCH WORKFLOW**:

When conducting research (if agent_name is mentioned in the request):
1. **Understand Context First**:
   - Query their holdings to see current positions
   - Review trade history for relevant stocks
   - Check past decisions to understand their investment thesis

2. **Combine Historical + Current**:
   - Use database to understand WHAT they hold and WHY
   - Use web search to find CURRENT news and market conditions
   - Synthesize both into context-aware research

3. **Return JSON Response** (MANDATORY):
   {{
     "summary": "Research findings referencing both historical context and current news",
     "sources": [
       {{"title": "Article Title", "url": "https://..."}}
     ]
   }}

**EXAMPLE RESEARCH FLOW**:

Request: "Research NVDA for Warren - considering buying more"

Step 1: query_holdings_tool("Warren")
→ See if Warren owns NVDA (e.g., 150 shares at avg $145)

Step 2: query_decisions_tool("Warren", "NVDA", 30)
→ Understand Warren's thesis: "Bought for AI datacenter growth, long-term hold"

Step 3: Brave Search "NVDA latest earnings AI chip demand 2025"
→ Get current news and analysis

Step 4: Synthesize
→ "Warren currently holds 150 NVDA (bought at $145 for AI growth thesis).
   Recent Q4 earnings beat expectations by 8% (TechCrunch), AI chip demand
   surging with datacenter expansion (Reuters). Current price $178 (+22.7% gain).
   Original thesis remains valid with strong fundamentals."

**IMPORTANT**:
- Make use of your knowledge graph to store and recall entity information
- Store information about companies, stocks, and market conditions
- Store web addresses for interesting sources
- Draw on your knowledge graph to build expertise over time
- ALWAYS include at least 2-3 sources with actual URLs from your searches
- DO NOT make up or hallucinate URLs

The current datetime is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    # Create list of database tools
    db_tools = [
        query_holdings_tool,
        query_trades_tool,
        query_decisions_tool,
        lookup_price_tool,
    ]

    researcher = Agent(
        name="Researcher",
        instructions=instructions,
        model=get_model(model_name),
        mcp_servers=mcp_servers,
        tools=db_tools,  # Add database tools
    )
    return researcher

async def get_researcher_tool(mcp_servers, model_name) -> Tool:
    """Create researcher tool following source project pattern exactly"""
    researcher = await get_researcher(mcp_servers, model_name)
    return researcher.as_tool(
        tool_name="Researcher", 
        tool_description="This tool researches online for news and opportunities, \
either based on your specific request to look into a certain stock, \
or generally for notable financial news and opportunities. \
Describe what kind of research you're looking for."
    )