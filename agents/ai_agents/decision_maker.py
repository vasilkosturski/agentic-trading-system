"""Decision Maker Agent - Decision Phase

This agent runs during the DECIDING phase to evaluate Market Analyst research
and make a BUY/SELL/HOLD decision. Has access to trading tools and can perform
additional research if needed.

Per design document: system-design/workflows/trade-execution/trade_exec_workflow_design.md
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from agents import Agent, Tool, function_tool
from agents.mcp import MCPServer

# Import backend client
from backend.client import get_backend_client
from config import config

# Import prompt loader
from infra.prompt_loader import load_and_format_prompt

# Import MCP types
from mcp_helpers.types import MCPName
from models.api_responses import RecentActivityResponse
from models.investment_style import InvestmentStyle

# Import models
from models.llm_output import ResearchResponse, TradingDecision

if TYPE_CHECKING:
    from mcp_helpers.types import MCPPool
    from models import Holding

logger = logging.getLogger(__name__)

# Position sizing limits by investment style (max % of portfolio per position)
POSITION_SIZING_PCT: dict[InvestmentStyle, int] = {
    InvestmentStyle.VALUE: 15,
    InvestmentStyle.CONTRARIAN_MACRO: 20,
    InvestmentStyle.RISK_PARITY: 15,
    InvestmentStyle.GROWTH: 25,
}

# Default if style doesn't match any known style
DEFAULT_POSITION_SIZING_PCT = 15


def get_position_sizing_pct(style: InvestmentStyle) -> int:
    """Get max position size percentage for an investment style.

    Args:
        style: InvestmentStyle enum value

    Returns:
        Max percentage of portfolio per position (e.g., 15 for 15%)
    """
    pct = POSITION_SIZING_PCT.get(style)
    if pct is not None:
        return pct
    logger.warning(f"Unknown agent style '{style}', using default {DEFAULT_POSITION_SIZING_PCT}%")
    return DEFAULT_POSITION_SIZING_PCT


# ============================================================================
# Typed Input Models for DecisionMaker
# ============================================================================


@dataclass
class DecisionContext:
    """Typed input context for Decision Maker.

    Receives typed models, converts to strings internally for prompts.
    Prices are carried inside research_response.candidates (CandidateStock objects).
    """

    agent_name: str
    agent_style: InvestmentStyle
    research_response: ResearchResponse
    balance: float
    holdings: list["Holding"]
    recent_activity: RecentActivityResponse | None = None
    force_trade: bool = False
    max_positions: int = 10

    @property
    def position_count(self) -> int:
        """Current number of positions."""
        return len(self.holdings)

    @property
    def holdings_summary(self) -> str:
        """Format holdings with quantity and price for prompt."""
        if not self.holdings:
            return "No current holdings."
        lines = []
        for h in self.holdings:
            lines.append(f"- {h.symbol}: {h.quantity} shares @ ${h.averagePrice:.2f} avg")
        return "\n".join(lines)

    @property
    def historical_context(self) -> str:
        """Convert recent activity to JSON string for prompt."""
        if not self.recent_activity:
            return "No recent trading activity."
        return self.recent_activity.model_dump_json()


class DecisionMaker:
    """Object-oriented Decision Maker agent.

    Encapsulates agent creation and prompt building with typed inputs.
    Converts typed models to strings internally for LLM consumption.

    Usage (async factory pattern):
        maker = await DecisionMaker.create(agent_name="Warren", agent_id=1, mcp_pool=pool)
        prompt = maker.build_prompt(context)
        result = await Runner.run(maker.agent, prompt)
    """

    # Class-level type annotations (PEP 526) for type checker support
    agent_name: str
    agent_id: int
    mcp_pool: "MCPPool | None"
    model_name: str
    agent_style: InvestmentStyle
    agent: Agent[TradingDecision]

    def __init__(self) -> None:
        """Private constructor. Use DecisionMaker.create() instead."""
        pass

    @classmethod
    async def create(
        cls,
        agent_name: str,
        agent_id: int,
        mcp_pool: "MCPPool | None" = None,
        model_name: str | None = None,
        agent_style: InvestmentStyle = InvestmentStyle.VALUE,
    ) -> "DecisionMaker":
        """Create Decision Maker with agent already initialized.

        Args:
            agent_name: Agent name (e.g., "Warren")
            agent_id: Agent ID for tools that need it
            mcp_pool: Optional MCP pool for additional research
            model_name: OpenAI model name to use. Defaults to config.OPENAI_MODEL.
            agent_style: Agent investment style (e.g., "Value Investor")

        Returns:
            DecisionMaker instance with agent ready to use
        """
        if model_name is None:
            model_name = config.OPENAI_MODEL
        instance = cls.__new__(cls)
        instance.agent_name = agent_name
        instance.agent_id = agent_id
        instance.mcp_pool = mcp_pool
        instance.model_name = model_name
        instance.agent_style = agent_style
        instance.agent = await create_decision_maker_agent(
            agent_name=agent_name,
            agent_id=agent_id,
            mcp_pool=mcp_pool,
            model_name=model_name,
            agent_style=agent_style,
        )
        return instance

    def build_prompt(self, context: DecisionContext) -> str:
        """Build decision prompt from typed context.

        Args:
            context: DecisionContext with typed models

        Returns:
            Formatted prompt string for LLM
        """
        return build_decision_prompt(
            research_response=context.research_response,
            balance=context.balance,
            position_count=context.position_count,
            max_positions=context.max_positions,
            holdings_summary=context.holdings_summary,
            historical_context=context.historical_context,
            force_trade=context.force_trade,
            agent_style=context.agent_style,
        )


async def create_decision_maker_agent(
    agent_name: str,
    agent_id: int,
    mcp_pool: "MCPPool | None" = None,
    model_name: str | None = None,
    agent_style: InvestmentStyle = InvestmentStyle.VALUE,
) -> Agent[TradingDecision]:
    """Create Decision Maker agent for decision phase.

    Args:
        agent_name: Agent name (e.g., "Warren")
        agent_id: Agent ID for tools that need it
        mcp_pool: Optional MCP pool for additional research
        model_name: OpenAI model name to use. Defaults to config.OPENAI_MODEL.
        agent_style: Agent investment style

    Returns:
        Agent configured for trading decisions with structured TradingDecision output

    Note:
        Agent personality is loaded from template files (prompts/decision_maker/{agent_name}.txt).
        Uses structured output (output_type=TradingDecision) instead of tool callback.
    """
    if model_name is None:
        model_name = config.OPENAI_MODEL
    # Load instructions from template file with position sizing parameter
    # (async + cached — see prompt_loader)
    position_sizing_pct = get_position_sizing_pct(agent_style)
    instructions = await load_and_format_prompt(
        "decision_maker",
        agent_name,
        datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        position_sizing_pct=str(position_sizing_pct),
    )

    # Create trading history tool
    @function_tool
    async def get_symbol_trade_history(symbol: str) -> str:
        """Get your complete trading history for a specific stock.

        Args:
            symbol: Stock symbol (e.g., "AAPL")

        Returns:
            JSON string with trade history for that symbol
        """
        client = get_backend_client()
        result = await client.get_trading_history(agent_id, symbol, days=90)
        # Serialize typed response to JSON for LLM consumption
        return result.model_dump_json()

    # Collect tools (no decide_action - using structured output instead)
    # Account data is passed inline in the decision prompt, no tool needed.
    tools: list[Tool] = [
        get_symbol_trade_history,
    ]

    # Add MCP servers if provided (dict access)
    mcp_servers: list[MCPServer] = []
    if mcp_pool:
        # Add Brave Search for additional research
        brave_server = mcp_pool.get(MCPName.BRAVE_SEARCH)
        if brave_server:
            mcp_servers.append(brave_server)

        # Add Fetch for web content
        fetch_server = mcp_pool.get(MCPName.FETCH)
        if fetch_server:
            mcp_servers.append(fetch_server)

    # Create agent with structured output enforcement
    trader = Agent[TradingDecision](
        name=f"{agent_name}-DecisionMaker",
        instructions=instructions,
        model=model_name,
        tools=tools,
        mcp_servers=mcp_servers,
        output_type=TradingDecision,  # Enforces schema compliance like Market Analyst
    )

    logger.info(
        f"✅ Created Decision Maker agent for {agent_name} with {len(tools)} tools and {len(mcp_servers)} MCP servers"
    )

    return trader


def build_decision_prompt(
    research_response: ResearchResponse,
    balance: float,
    position_count: int,
    max_positions: int,
    holdings_summary: str,
    historical_context: str,
    force_trade: bool = False,
    agent_style: InvestmentStyle = InvestmentStyle.VALUE,
) -> str:
    """Build the decision prompt for Decision Maker agent.

    Args:
        research_response: Market Analyst research results (candidates carry prices)
        balance: Available cash balance
        position_count: Current number of positions
        max_positions: Maximum positions allowed (10)
        holdings_summary: Summary of current holdings
        historical_context: Recent trading history
        force_trade: Whether agent MUST make a trade (no HOLD allowed)
        agent_style: Investment style for position sizing rules

    Returns:
        Formatted prompt string
    """
    position_sizing_pct = get_position_sizing_pct(agent_style)
    max_position_value = balance * position_sizing_pct / 100.0

    # Format research candidates with prices from CandidateStock objects
    candidate_lines = []
    for candidate in research_response.candidates:
        candidate_lines.append(f"- {candidate.symbol} (current price: ${candidate.price:,.2f})")
    candidates_text = "\n".join(candidate_lines)

    # Format research sources
    sources_text = "\n".join(
        [f"- {source.title}: {source.url}" for source in research_response.webSources]
    )

    prompt = f"""Time to make your trading decision.

**Market Analyst Research:**

{research_response.summary}

**Candidates Identified:**
{candidates_text if candidates_text else "None"}

**Research Sources:**
{sources_text if sources_text else "None"}

**Your Current Portfolio:**
- Balance: ${balance:,.2f}
- Positions: {position_count}/{max_positions}
- Holdings: {holdings_summary if holdings_summary else "None"}

**Recent Trading History:**
{historical_context if historical_context else "No recent trades"}

"""

    # Add price-based budget constraint (prices always available via CandidateStock)
    if research_response.candidates:
        prompt += f"""**BUDGET CONSTRAINT (MANDATORY):**
- total_cost = quantity x price_per_share
- total_cost MUST be <= available cash balance (${balance:,.2f})
- If you cannot afford at least 1 share, do NOT pick that candidate
"""

    # Add position sizing constraint (always, reinforces the system prompt rule)
    prompt += f"""**POSITION SIZING CONSTRAINT (MANDATORY):**
- Max {position_sizing_pct}% of portfolio per position
- max_position_value = ${max_position_value:,.2f}
- total_cost for any single trade MUST be <= ${max_position_value:,.2f}
- This prevents over-concentration in any single holding
"""

    if force_trade:
        prompt += """
**CRITICAL: You MUST make a trade this cycle (BUY or SELL).**
- HOLD is NOT an option
- Choose the best opportunity from the research
- If no good BUY candidates, consider SELL decision to rebalance
"""
    else:
        prompt += """
**Decision Options:**
- BUY: If you find a compelling opportunity
- SELL: If you want to exit a position
- HOLD: If no action is warranted right now
"""

    if position_count >= max_positions:
        prompt += """

**Position Limit Reached:**
- You have 10 positions (maximum allowed)
- You CANNOT open new positions
- You CAN add to existing positions
- You CAN sell any position to make room
"""

    prompt += """

Make your decision now."""

    return prompt
