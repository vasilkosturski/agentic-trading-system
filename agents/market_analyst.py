"""Market Analyst Agent - Research Phase

This agent runs during the RESEARCHING phase to find 3-5 stock candidates
matching the agent's investment style. Uses Brave Search + Fetch MCPs for
web research, plus database tools to check current portfolio context.

Dual-Prompt Architecture
------------------------
This module uses TWO separate prompts that work together:

1. **System/Instructions Prompt** (from template files):
   - Location: prompts/market_analyst/{agent_name}.txt (e.g., warren.txt)
   - Loaded by: load_and_format_prompt() in prompt_loader.py
   - Purpose: Defines WHO the agent is (personality, investment style, criteria)
   - Used as: `instructions` parameter when creating the Agent
   - Fixed per agent personality

2. **Task/User Prompt** (from build_research_prompt()):
   - Built by: build_research_prompt() function below
   - Purpose: Defines WHAT to do now (current context, balance, holdings)
   - Used as: The message passed to Runner.run(agent, prompt)
   - Changes each trading cycle with fresh data

How they combine:
    # 1. Create agent with personality (from template)
    analyst = await create_market_analyst_agent(agent_name, ...)

    # 2. Build task prompt with current context
    research_prompt = build_research_prompt(balance, holdings, ...)

    # 3. Run agent: system prompt + user prompt
    result = await Runner.run(analyst, research_prompt)

Per design document: system-design/workflows/trade-execution/trade_exec_workflow_design.md
"""

import json
import logging
from dataclasses import dataclass
from agents import Agent, function_tool
from datetime import datetime
from typing import Union, List, TYPE_CHECKING

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
from models.mcp_types import MCPServerName
from http_client import BackendAPIError
from pydantic import ValidationError

if TYPE_CHECKING:
    from mcp_types import MCPPool
    from models import Holding

logger = logging.getLogger(__name__)


# ============================================================================
# Typed Input Models for MarketAnalyst
# ============================================================================

@dataclass
class ResearchContext:
    """Typed input context for Market Analyst research.

    Receives typed models, converts to strings internally for prompts.
    """
    agent_name: str
    agent_style: str
    balance: float
    holdings: List["Holding"]
    recent_activity: RecentActivityResponse
    max_positions: int = 10

    @property
    def position_count(self) -> int:
        """Current number of positions."""
        return len(self.holdings)

    @property
    def holdings_summary(self) -> str:
        """Convert holdings to JSON string for prompt."""
        return json.dumps([h.symbol for h in self.holdings]) if self.holdings else "[]"

    @property
    def historical_context(self) -> str:
        """Convert recent activity to JSON string for prompt."""
        return self.recent_activity.model_dump_json()


class MarketAnalyst:
    """Object-oriented Market Analyst agent.

    Encapsulates agent creation and prompt building with typed inputs.
    Converts typed models to strings internally for LLM consumption.

    Usage (async factory pattern):
        analyst = await MarketAnalyst.create(agent_name="Warren", mcp_pool=pool)
        prompt = analyst.build_prompt(context)
        result = await Runner.run(analyst.agent, prompt)
    """

    # Class-level type annotations (PEP 526) for type checker support
    agent_name: str
    mcp_pool: "MCPPool"
    model_name: str
    agent: Agent[ResearchResponse]

    def __init__(self) -> None:
        """Private constructor. Use MarketAnalyst.create() instead."""
        pass

    @classmethod
    async def create(
        cls,
        agent_name: str,
        mcp_pool: "MCPPool",
        model_name: str = "gpt-4o-mini",
    ) -> "MarketAnalyst":
        """Create Market Analyst with agent already initialized.

        Args:
            agent_name: Agent name (e.g., "Warren")
            mcp_pool: MCP pool with Brave Search + Fetch servers
            model_name: Model to use (default: gpt-4o-mini)

        Returns:
            MarketAnalyst instance with agent ready to use
        """
        instance = cls.__new__(cls)
        instance.agent_name = agent_name
        instance.mcp_pool = mcp_pool
        instance.model_name = model_name
        instance.agent = await create_market_analyst_agent(
            agent_name=agent_name,
            mcp_pool=mcp_pool,
            model_name=model_name,
        )
        return instance

    def build_prompt(self, context: ResearchContext) -> str:
        """Build research prompt from typed context.

        Args:
            context: ResearchContext with typed models

        Returns:
            Formatted prompt string for LLM
        """
        return build_research_prompt(
            agent_name=context.agent_name,
            agent_style=context.agent_style,
            balance=context.balance,
            position_count=context.position_count,
            max_positions=context.max_positions,
            holdings_summary=context.holdings_summary,
            historical_context=context.historical_context,
        )


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
    brave_server = await mcp_pool.get_server(MCPServerName.BRAVE_SEARCH)
    if brave_server:
        mcp_servers.append(brave_server)
    else:
        logger.warning("Brave Search MCP server not available for Market Analyst")

    # Add Fetch server
    fetch_server = await mcp_pool.get_server(MCPServerName.FETCH)
    if fetch_server:
        mcp_servers.append(fetch_server)
    else:
        logger.warning("Fetch MCP server not available for Market Analyst")

    # Add Memory server (optional, for context)
    memory_server = await mcp_pool.get_server(MCPServerName.MEMORY)
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

    Returns:
        Formatted prompt string
    """
    # Calculate near-capacity threshold (70% of max)
    near_capacity_threshold = int(max_positions * 0.7)

    prompt = f"""Research candidates for {agent_name}'s portfolio review.

**Agent Style:** {agent_style}

**Recent Trading Activity:**
{historical_context if historical_context != "{}" else "No recent trades"}

**Current Portfolio Context:**
- Balance: ${balance:,.2f}
- Positions: {position_count}/{max_positions}
- Current holdings: {holdings_summary if holdings_summary else "None"}

**Your Task:**
Research and identify 3-5 stock candidates that match {agent_name}'s {agent_style} investment style.

**Research Focus:**
"""

    if position_count >= max_positions:
        prompt += f"""
- Portfolio is at maximum capacity ({max_positions} positions)
- Focus on comparing new candidates vs. current holdings
- Consider whether any current holdings should be replaced
"""
    elif position_count >= near_capacity_threshold:
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
