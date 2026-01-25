"""Market Analyst Agent - Research Phase

This agent runs during the RESEARCHING phase to find 3-5 stock candidates
matching the agent's investment style. Uses Brave Search + Fetch MCPs for
web research, plus database tools to check current portfolio context.

Per design document: system-design/workflows/trade-execution/trade_exec_workflow_design.md
"""

import logging
from agents import Agent, function_tool
from datetime import datetime
from typing import Union, TYPE_CHECKING

# Import model for structured output
from models.llm_output import ResearchResponse

# Import prompt loader
from prompt_loader import load_and_format_prompt

# Import data layer functions from researcher (reuse existing implementation)
from researcher import (
    _fetch_holdings,
    _fetch_recent_activity,
    _fetch_price,
)
from models import (
    HoldingsResponse,
    RecentActivityResponse,
    PriceLookupResponse,
    ToolError,
)
from http_client import BackendAPIError
from pydantic import ValidationError

if TYPE_CHECKING:
    from mcp_types import MCPPool

logger = logging.getLogger(__name__)


async def create_market_analyst_agent(
    agent_name: str,
    mcp_pool: "MCPPool",
    model_name: str = "gpt-4o-mini",
) -> Agent[ResearchResponse]:
    """Create Market Analyst agent for research phase.

    Args:
        agent_name: Agent name (e.g., "Warren")
        mcp_pool: MCP pool with Brave Search + Fetch servers
        model_name: Model to use (default: gpt-4o-mini)

    Returns:
        Agent configured for research with ResearchResponse output type
    
    Note:
        Agent personality is loaded from template files (prompts/market_analyst/{agent_name}.txt).
    """
    # Load instructions from template file
    instructions = load_and_format_prompt(
        "market_analyst",
        agent_name,
        datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    # Create database tools for portfolio context
    @function_tool
    async def query_holdings_tool() -> Union[HoldingsResponse, ToolError]:
        """Get current portfolio holdings to avoid recommending stocks already heavily weighted.

        Returns:
            Current holdings with symbols, quantities, and values
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
    async def query_recent_activity_tool(days: int = 30) -> Union[RecentActivityResponse, ToolError]:
        """Get recent trading activity to understand context and avoid repetitive recommendations.

        Args:
            days: How many days back to look (default: 30)

        Returns:
            Recent trades and decisions
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
    async def lookup_price_tool(symbol: str) -> Union[PriceLookupResponse, ToolError]:
        """Get current market price to check if candidates fit budget constraints.

        Args:
            symbol: Stock symbol (e.g., AAPL, NVDA)

        Returns:
            Current stock price
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

    # Collect database tools
    db_tools = [
        query_holdings_tool,
        query_recent_activity_tool,
        lookup_price_tool,
    ]

    # Get MCP servers for research
    mcp_servers = []

    # Add Brave Search server
    brave_server = await mcp_pool.get_server("brave-search")
    if brave_server:
        mcp_servers.append(brave_server)
    else:
        logger.warning("Brave Search MCP server not available for Market Analyst")

    # Add Fetch server
    fetch_server = await mcp_pool.get_server("fetch")
    if fetch_server:
        mcp_servers.append(fetch_server)
    else:
        logger.warning("Fetch MCP server not available for Market Analyst")

    # Add Memory server (optional, for context)
    memory_server = await mcp_pool.get_server("memory")
    if memory_server:
        mcp_servers.append(memory_server)

    # Create agent with structured output enforcement
    analyst = Agent[ResearchResponse](
        name=f"{agent_name}-MarketAnalyst",
        instructions=instructions,
        model=model_name,
        mcp_servers=mcp_servers,
        tools=db_tools,
        output_type=ResearchResponse,  # Enforces schema compliance
    )

    logger.info(
        f"✅ Created Market Analyst agent for {agent_name} with {len(db_tools)} tools and {len(mcp_servers)} MCP servers"
    )

    return analyst


def build_research_prompt(
    agent_name: str,
    agent_style: str,
    balance: float,
    position_count: int,
    max_positions: int,
    holdings_summary: str,
    historical_context: str = "{}",
    force_trade: bool = False,
) -> str:
    """Build the research prompt for Market Analyst.

    Args:
        agent_name: Agent name
        agent_style: Investment style (e.g., "Value Investor")
        balance: Available cash balance
        position_count: Current number of positions
        max_positions: Maximum positions allowed (10)
        holdings_summary: Summary of current holdings
        historical_context: JSON string with recent trading activity
        force_trade: Whether agent must find candidates (not used by analyst)

    Returns:
        Formatted prompt string
    """
    prompt = f"""Research candidates for {agent_name}'s portfolio review.

**Agent Style:** {agent_style}

**Current Portfolio Context:**
- Balance: ${balance:,.2f}
- Positions: {position_count}/{max_positions}
- Current holdings: {holdings_summary if holdings_summary else "None"}

**Your Task:**
Research and identify 3-5 stock candidates that match {agent_name}'s {agent_style} investment style.

**Research Focus:**
"""

    if position_count >= max_positions:
        prompt += """
- Portfolio is at maximum capacity (10 positions)
- Focus on comparing new candidates vs. current holdings
- Consider whether any current holdings should be replaced
"""
    elif position_count >= 7:
        prompt += """
- Portfolio is near capacity
- Prioritize high-conviction ideas
- Be selective with new positions
"""
    else:
        prompt += """
- Portfolio has room for growth
- Search broadly for opportunities
- Consider diversification
"""

    prompt += """

**Deliverables:**
1. List of 3-5 stock candidates with ticker symbols
2. Research summary explaining why each fits the strategy
3. Web sources for all claims (titles + URLs)
4. Any risks or concerns identified

Begin your research now."""

    return prompt
