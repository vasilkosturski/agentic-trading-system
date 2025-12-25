#!/usr/bin/env python3
"""
Researcher Agent - Financial research with database and web capabilities.

Structure:
- get_researcher_instructions() → System prompt
- build_research_message(query) → Invocation context  
- create_researcher_agent(...) → Create agent with typed output
- run_researcher(query, ...) → Execute and return ResearchResponse

The researcher is stateless - each query is independent.
Agent names and other context come from the query itself.

To use as a tool from another agent:
    researcher = await create_researcher_agent(mcp_servers, model)
    tool = researcher.as_tool(tool_name="Researcher", tool_description="...")
"""

from agents import Agent, Runner, function_tool
from datetime import datetime
from textwrap import dedent
from typing import Union
from pydantic import ValidationError
from config import BACKEND_BASE_URL
from http_client import call_backend, BackendAPIError
from models import (
    ResearchResponse,
    HoldingsResponse,
    RecentActivityResponse,
    SymbolHistoryResponse,
    PriceLookupResponse,
    ToolError,
)
from mcp_types import MCPName, MCPPool


# =============================================================================
# MCP Requirements - Declare what this agent needs
# =============================================================================

REQUIRED_MCPS = [MCPName.BRAVE_SEARCH, MCPName.FETCH]


# =============================================================================
# Data layer functions (internal - return typed models)
# =============================================================================

async def _fetch_holdings(agent_name: str) -> HoldingsResponse:
    """Fetch holdings from backend API.
    
    Args:
        agent_name: Name of the trading agent
        
    Returns:
        HoldingsResponse with agent's current holdings
        
    Raises:
        BackendAPIError: If the API call fails
    """
    url = f"{BACKEND_BASE_URL}/api/memory/holdings"
    params = {"agentName": agent_name}
    response = await call_backend("GET", url, params=params, timeout=10)
    return HoldingsResponse.model_validate_json(response.text)


async def _fetch_recent_activity(agent_name: str, days: int) -> RecentActivityResponse:
    """Fetch recent activity from backend API.
    
    Args:
        agent_name: Name of the trading agent
        days: Number of days to look back
        
    Returns:
        RecentActivityResponse with recent trading runs
        
    Raises:
        BackendAPIError: If the API call fails
    """
    url = f"{BACKEND_BASE_URL}/api/memory/recent-activity"
    params = {"agentName": agent_name, "days": days}
    response = await call_backend("GET", url, params=params, timeout=10)
    return RecentActivityResponse.model_validate_json(response.text)


async def _fetch_symbol_history(agent_name: str, symbol: str, days: int) -> SymbolHistoryResponse:
    """Fetch symbol trading history from backend API.
    
    Args:
        agent_name: Name of the trading agent
        symbol: Stock symbol (e.g., AAPL)
        days: Number of days to look back
        
    Returns:
        SymbolHistoryResponse with trading history for the symbol
        
    Raises:
        BackendAPIError: If the API call fails
    """
    url = f"{BACKEND_BASE_URL}/api/memory/trading-history"
    params = {"agentName": agent_name, "symbol": symbol, "days": days}
    response = await call_backend("GET", url, params=params, timeout=10)
    return SymbolHistoryResponse.model_validate_json(response.text)


async def _fetch_price(symbol: str) -> PriceLookupResponse:
    """Fetch current price from market tools.
    
    Args:
        symbol: Stock symbol (e.g., AAPL)
        
    Returns:
        PriceLookupResponse with current price
        
    Raises:
        Exception: If price lookup fails
    """
    from market_tools import lookup_share_price
    price = await lookup_share_price(symbol)
    return PriceLookupResponse(
        symbol=symbol,
        price=price,
        timestamp=datetime.now().isoformat()
    )


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

**RESEARCH WORKFLOW**:

When conducting research (agent_name is required in every request):
1. **Understand Context First**:
   - Query their holdings to see current positions
   - Use query_recent_activity_tool for general overview
   - Use query_symbol_history_tool for specific stock details
   - Use lookup_price_tool for current market prices

2. **Combine Historical + Current**:
   - Use database to understand WHAT they hold and WHY
   - Use web search to find CURRENT news and market conditions
   - Synthesize both into context-aware research

**IMPORTANT**:
- ALWAYS include at least 2-3 sources with actual URLs from your searches
- DO NOT make up or hallucinate URLs
"""


def _build_research_message(query: str) -> str:
    """Build user message for this research request (internal helper).

    Args:
        query: The research query/request

    Returns:
        User message for this invocation
    """
    return dedent(f"""
        Current time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        Research request: {query}
    """).strip()


async def create_researcher_agent(mcp_pool: MCPPool, model_name: str) -> Agent[ResearchResponse]:
    """Create researcher agent with typed output.

    The researcher is stateless - agent names come from the query.
    Uses output_type=ResearchResponse to enforce structured output from LLM.

    Args:
        mcp_pool: MCP pool - agent selects servers from REQUIRED_MCPS
        model_name: Model to use

    Returns:
        Agent configured for typed ResearchResponse output
    """
    # Select only the MCPs this agent needs
    mcp_servers = [mcp_pool[mcp_name] for mcp_name in REQUIRED_MCPS if mcp_name in mcp_pool]
    @function_tool
    async def query_holdings_tool(agent_name: str) -> Union[HoldingsResponse, ToolError]:
        """Get current holdings for a trading agent.

        Args:
            agent_name: Agent name (Warren, George, Ray, Cathie)
        """
        try:
            return await _fetch_holdings(agent_name)
        except BackendAPIError as e:
            if e.status_code == 404:
                return ToolError(
                    error="Agent not found",
                    error_type="not_found",
                    context={"agent_name": agent_name}
                )
            return ToolError(
                error=str(e),
                error_type="api_error",
                context={"agent_name": agent_name}
            )
        except ValidationError as e:
            return ToolError(
                error=f"Invalid data from backend: {e}",
                error_type="validation",
                context={"agent_name": agent_name}
            )
        except Exception as e:
            return ToolError(
                error=f"Unexpected error: {e}",
                error_type="unknown",
                context={"agent_name": agent_name}
            )

    @function_tool
    async def query_recent_activity_tool(agent_name: str, days: int = 30) -> Union[RecentActivityResponse, ToolError]:
        """Get recent activity across ALL stocks for an agent.

        Args:
            agent_name: Agent name (Warren, George, Ray, Cathie)
            days: How many days back to look
        """
        try:
            return await _fetch_recent_activity(agent_name, days)
        except BackendAPIError as e:
            if e.status_code == 404:
                return ToolError(
                    error="No recent activity found",
                    error_type="not_found",
                    context={"agent_name": agent_name, "days": days}
                )
            return ToolError(
                error=str(e),
                error_type="api_error",
                context={"agent_name": agent_name, "days": days}
            )
        except ValidationError as e:
            return ToolError(
                error=f"Invalid data from backend: {e}",
                error_type="validation",
                context={"agent_name": agent_name, "days": days}
            )
        except Exception as e:
            return ToolError(
                error=f"Unexpected error: {e}",
                error_type="unknown",
                context={"agent_name": agent_name, "days": days}
            )

    @function_tool
    async def query_symbol_history_tool(agent_name: str, symbol: str, days: int = 30) -> Union[SymbolHistoryResponse, ToolError]:
        """Get trading history for a SPECIFIC stock.

        Args:
            agent_name: Agent name (Warren, George, Ray, Cathie)
            symbol: Stock symbol (e.g., AAPL, NVDA)
            days: How many days back to look
        """
        try:
            return await _fetch_symbol_history(agent_name, symbol, days)
        except BackendAPIError as e:
            if e.status_code == 404:
                return ToolError(
                    error=f"No history found for {symbol}",
                    error_type="not_found",
                    context={"agent_name": agent_name, "symbol": symbol, "days": days}
                )
            return ToolError(
                error=str(e),
                error_type="api_error",
                context={"agent_name": agent_name, "symbol": symbol, "days": days}
            )
        except ValidationError as e:
            return ToolError(
                error=f"Invalid data from backend: {e}",
                error_type="validation",
                context={"agent_name": agent_name, "symbol": symbol, "days": days}
            )
        except Exception as e:
            return ToolError(
                error=f"Unexpected error: {e}",
                error_type="unknown",
                context={"agent_name": agent_name, "symbol": symbol, "days": days}
            )

    @function_tool
    async def lookup_price_tool(symbol: str) -> Union[PriceLookupResponse, ToolError]:
        """Get current market price for a stock.
        
        Args:
            symbol: Stock symbol (e.g., AAPL, NVDA)
        """
        try:
            return await _fetch_price(symbol)
        except ValidationError as e:
            return ToolError(
                error=f"Invalid price data: {e}",
                error_type="validation",
                context={"symbol": symbol}
            )
        except Exception as e:
            return ToolError(
                error=str(e),
                error_type="api_error",
                context={"symbol": symbol}
            )

    db_tools = [
        query_holdings_tool,
        query_recent_activity_tool,
        query_symbol_history_tool,
        lookup_price_tool,
    ]

    return Agent[ResearchResponse](
        name="Researcher",
        instructions=get_researcher_instructions(),
        model=model_name,
        mcp_servers=mcp_servers,
        tools=db_tools,
        output_type=ResearchResponse,  # Enforces typed output
    )


async def run_researcher(
    query: str,
    mcp_pool: MCPPool,
    model_name: str = "gpt-4o-mini",
) -> ResearchResponse:
    """Run researcher agent independently and return typed response.

    This is the main entry point for standalone use or testing.
    The query should contain all necessary context (agent names, etc).

    Args:
        query: Research request (include agent name if querying agent data)
        mcp_pool: MCP pool - agent selects servers from REQUIRED_MCPS
        model_name: Model to use

    Returns:
        ResearchResponse with validated summary and sources

    Raises:
        AgentError: If the agent fails to produce valid output

    Example:
        # Research for a specific agent
        response = await run_researcher(
            "I am Warren. Review my holdings and check for news on each position.",
            mcp_pool
        )

        # General research
        response = await run_researcher(
            "What's the latest news on NVDA?",
            mcp_pool
        )
    """
    agent = await create_researcher_agent(mcp_pool, model_name)
    message = _build_research_message(query)

    result = await Runner.run(agent, message)

    # With output_type set, final_output is already a validated ResearchResponse
    return result.final_output

