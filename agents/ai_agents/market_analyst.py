"""Market Analyst Agent - Research Phase

This agent runs during the RESEARCHING phase to find 3-5 stock candidates
matching the agent's investment style. Uses Brave Search + Fetch MCPs for
web research, plus a price lookup tool for budget verification.

Portfolio context (holdings, recent activity) is passed inline in the task
prompt — the agent_executor pre-fetches this data, so no redundant API calls
are needed.

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
   - Purpose: Defines WHAT to do now (current context, balance, position count)
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

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    Runner,
    Tool,
    function_tool,
    output_guardrail,
)
from agents.mcp import MCPServer
from pydantic import ValidationError

from config import config

# Import prompt loader
from infra.prompt_loader import load_and_format_prompt
from mcp_helpers.types import MCPName
from models import (
    AgentRunResult,
    RecentActivityResponse,
    ToolError,
)
from models.investment_style import InvestmentStyle

# Import model for structured output
from models.llm_output import ResearchResponse
from tools.market_tools import _lookup_share_price
from utils.sdk_parser import extract_tool_calls, get_tool_errors

if TYPE_CHECKING:
    from mcp_helpers.types import MCPPool
    from models import Holding

logger = logging.getLogger(__name__)


# ============================================================================
# Output Guardrail
# ============================================================================

_PLACEHOLDER_DOMAINS = {"example.com", "example.org", "example.net", "placeholder.com"}


@output_guardrail
async def validate_research_output(
    ctx: RunContextWrapper, agent: Agent, output: ResearchResponse
) -> GuardrailFunctionOutput:
    """Validate that Market Analyst produced actionable research.

    Checks:
    - candidates and webSources are non-empty
    - candidates have positive prices
    - webSources contain real URLs, not placeholder/hallucinated domains
    """
    issues: list[str] = []
    if not output.candidates:
        issues.append("candidates is empty")
    else:
        no_price = [c.symbol for c in output.candidates if c.price <= 0]
        if no_price:
            issues.append(
                f"candidates with unavailable prices (-1.0 sentinel): {no_price}. "
                "Agent should have excluded these symbols from final candidates list."
            )
    if not output.webSources:
        issues.append("webSources is empty")
    else:
        # Detect hallucinated URLs — model sometimes fabricates sources
        # instead of using brave_web_search
        fake = [s.url for s in output.webSources if any(d in s.url for d in _PLACEHOLDER_DOMAINS)]
        if fake:
            issues.append(
                f"webSources contain placeholder URLs (use brave_web_search "
                f"for real sources): {fake}"
            )
    return GuardrailFunctionOutput(
        output_info={"issues": issues},
        tripwire_triggered=len(issues) > 0,
    )


# ============================================================================
# Typed Input Models for MarketAnalyst
# ============================================================================


@dataclass
class MarketAnalystContext:
    """Typed input context for Market Analyst research.

    Receives typed models, converts to strings internally for prompts.
    """

    agent_name: str
    agent_style: InvestmentStyle
    balance: float
    holdings: list["Holding"]
    recent_activity: RecentActivityResponse | None = None
    max_positions: int = 10

    @property
    def position_count(self) -> int:
        """Current number of positions."""
        return len(self.holdings)

    @property
    def holdings_summary(self) -> str:
        """Format holdings as a readable string for inline prompt inclusion."""
        if not self.holdings:
            return "No current holdings."
        lines = [f"Current Holdings ({self.position_count} positions):"]
        for h in self.holdings:
            lines.append(f"- {h.symbol}: {h.quantity} shares @ ${h.averagePrice:.2f} avg")
        return "\n".join(lines)

    @property
    def historical_context(self) -> str:
        """Format recent activity as a readable string for inline prompt inclusion."""
        if not self.recent_activity or not self.recent_activity.runs:
            return "No recent trading activity."
        lines = [f"Recent Activity ({len(self.recent_activity.runs)} runs):"]
        for run in self.recent_activity.runs[:5]:
            summary = run.summary[:100] if run.summary else "No summary"
            trade_count = len(run.trades) if run.trades else 0
            trades_str = f", {trade_count} trades" if trade_count > 0 else ", no trades"
            lines.append(f"- {run.date}: {run.outcome}{trades_str} — {summary}")
        return "\n".join(lines)


class MarketAnalyst:
    """Object-oriented Market Analyst agent.

    Encapsulates agent creation, prompt building, and execution with typed inputs.
    Converts typed models to strings internally for LLM consumption.

    Usage (async factory pattern):
        analyst = await MarketAnalyst.create(agent_name="Warren", mcp_pool=pool)
        response = await analyst.run(context)  # Returns ResearchResponse directly
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
        model_name: str | None = None,
    ) -> "MarketAnalyst":
        """Create Market Analyst with agent already initialized.

        Args:
            agent_name: Agent name (e.g., "Warren")
            mcp_pool: MCP pool with Brave Search + Fetch servers
            model_name: OpenAI model name to use. Defaults to config.OPENAI_MODEL.

        Returns:
            MarketAnalyst instance with agent ready to use
        """
        if model_name is None:
            model_name = config.OPENAI_MODEL
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

    def build_prompt(self, context: MarketAnalystContext) -> str:
        """Build research prompt from typed context.

        Args:
            context: MarketAnalystContext with typed models

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

    async def run(
        self, context: MarketAnalystContext, max_turns: int = 15
    ) -> AgentRunResult[ResearchResponse]:
        """Run market analyst agent and return result with full visibility.

        Encapsulates prompt building, agent execution, and response extraction.
        Returns tool errors in result - caller decides how to handle.

        Args:
            context: MarketAnalystContext with typed models
            max_turns: Maximum agent turns (default: 15)

        Returns:
            AgentRunResult containing:
            - output: ResearchResponse with candidates, summary, and sources
            - tool_calls: All tool calls made during execution
            - tool_errors: Any tools that returned error responses

        Raises:
            MaxTurnsExceeded: If agent doesn't complete within max_turns

        Usage:
            result = await analyst.run(context)
            result.raise_if_errors()  # Opt-in fail-fast
            # OR check result.has_errors for graceful handling
        """
        prompt = self.build_prompt(context)
        result = await Runner.run(self.agent, prompt, max_turns=max_turns)

        # Extract tool calls for visibility
        tool_calls = extract_tool_calls(result.new_items)
        tool_errors = get_tool_errors(tool_calls)

        # Log errors but let caller decide how to handle
        if tool_errors:
            error_details = "; ".join([f"{e.name}: {e.output[:100]}" for e in tool_errors])
            logger.warning(f"Tool errors detected (caller decides handling): {error_details}")

        # Return result with full visibility - caller calls raise_if_errors() if they want fail-fast
        return AgentRunResult(
            output=result.final_output_as(ResearchResponse),
            tool_calls=tool_calls,
            tool_errors=tool_errors,
        )


async def create_market_analyst_agent(
    agent_name: str,
    mcp_pool: "MCPPool",
    model_name: str | None = None,
) -> Agent[ResearchResponse]:
    """Create Market Analyst agent for research phase.

    Args:
        agent_name: Agent name (e.g., "Warren")
        mcp_pool: MCP pool with Brave Search + Fetch servers
        model_name: OpenAI model name to use. Defaults to config.OPENAI_MODEL.

    Returns:
        Agent configured for research with ResearchResponse output type

    Note:
        Agent personality is loaded from template files (prompts/market_analyst/{agent_name}.txt).
    """
    if model_name is None:
        model_name = config.OPENAI_MODEL
    # Load instructions from template file (async + cached — see prompt_loader)
    instructions = await load_and_format_prompt(
        "market_analyst",
        agent_name,
        datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    # Create price lookup tool for budget verification
    @function_tool
    async def lookup_price_tool(symbol: str) -> dict | ToolError:
        """Get current market price to check if candidates fit budget constraints.

        Args:
            symbol: Stock symbol (e.g., AAPL, NVDA)

        Returns:
            Dict with symbol, price, and timestamp (JSON-serializable by SDK)
        """
        try:
            price = await _lookup_share_price(symbol)
            return {
                "symbol": symbol.upper(),
                "price": price,
                "timestamp": datetime.now().isoformat(),
            }
        except ValidationError as e:
            return ToolError(
                error=f"Invalid price data: {e}",
                error_type="validation",
                context={"symbol": symbol},
            )
        except Exception as e:
            return ToolError(error=str(e), error_type="api_error", context={"symbol": symbol})

    # Collect tools (price lookup only — holdings/activity passed inline)
    db_tools: list[Tool] = [
        lookup_price_tool,
    ]

    # Get MCP servers for research (dict access)
    mcp_servers: list[MCPServer] = []

    # Add Brave Search server
    brave_server = mcp_pool.get(MCPName.BRAVE_SEARCH)
    if brave_server:
        mcp_servers.append(brave_server)
    else:
        logger.warning("Brave Search MCP server not available for Market Analyst")

    # Add Fetch server
    fetch_server = mcp_pool.get(MCPName.FETCH)
    if fetch_server:
        mcp_servers.append(fetch_server)
    else:
        logger.warning("Fetch MCP server not available for Market Analyst")

    # Create agent with structured output enforcement
    analyst = Agent[ResearchResponse](
        name=f"{agent_name}-MarketAnalyst",
        instructions=instructions,
        model=model_name,
        mcp_servers=mcp_servers,
        tools=db_tools,
        output_type=ResearchResponse,  # Enforces schema compliance
        output_guardrails=[validate_research_output],
    )

    logger.info(
        f"✅ Created Market Analyst agent for {agent_name} with {len(db_tools)} tools and {len(mcp_servers)} MCP servers"
    )

    return analyst


def build_research_prompt(
    agent_name: str,
    agent_style: InvestmentStyle,
    balance: float,
    position_count: int,
    max_positions: int,
    holdings_summary: str,
    historical_context: str,
) -> str:
    """Build the research prompt for Market Analyst.

    Portfolio context (holdings, recent activity) is included inline in the
    prompt. The agent_executor pre-fetches this data, avoiding redundant
    API calls from the LLM.

    Args:
        agent_name: Agent name
        agent_style: Investment style enum value
        balance: Available cash balance
        position_count: Current number of positions
        max_positions: Maximum positions allowed (10)
        holdings_summary: Pre-formatted holdings string
        historical_context: Pre-formatted recent activity string

    Returns:
        Formatted prompt string
    """
    # Calculate near-capacity threshold (70% of max)
    near_capacity_threshold = int(max_positions * 0.7)

    prompt = f"""Research candidates for {agent_name}'s portfolio review.

**Agent Style:** {agent_style}

**Current Portfolio Context:**
- Balance: ${balance:,.2f}
- Positions: {position_count}/{max_positions}
- Current holdings:
{holdings_summary}
- Recent activity:
{historical_context}

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

Begin your research now."""

    return prompt
