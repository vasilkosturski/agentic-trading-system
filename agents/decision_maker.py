"""Decision Maker Agent - Decision Phase

This agent runs during the DECIDING phase to evaluate Market Analyst research
and make a BUY/SELL/HOLD decision. Has access to trading tools and can perform
additional research if needed.

Per design document: system-design/workflows/trade-execution/trade_exec_workflow_design.md
"""

import logging
import json
from dataclasses import dataclass
from agents import Agent, Runner, function_tool
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

# Import models
from models.llm_output import TradingDecision, ResearchResponse
from models.api_responses import RecentActivityResponse
from models import AgentRunResult

# Import SDK parsing utilities
from utils.sdk_parser import extract_tool_calls, get_tool_errors

# Import trading and memory tools
from trading_tools import _get_balance_raw, _get_holdings_raw
from memory_tools import get_trading_history

# Import prompt loader
from prompt_loader import load_and_format_prompt

# Import MCP types
from mcp_types import MCPName

if TYPE_CHECKING:
    from mcp_types import MCPPool
    from models import Holding

logger = logging.getLogger(__name__)


# ============================================================================
# Typed Input Models for DecisionMaker
# ============================================================================

@dataclass
class DecisionContext:
    """Typed input context for Decision Maker.

    Receives typed models, converts to strings internally for prompts.
    """
    agent_name: str
    agent_style: str
    research_response: ResearchResponse
    balance: float
    holdings: List["Holding"]
    recent_activity: RecentActivityResponse
    force_trade: bool = False
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
    mcp_pool: Optional["MCPPool"]
    model_name: str
    agent: Agent[TradingDecision]

    def __init__(self) -> None:
        """Private constructor. Use DecisionMaker.create() instead."""
        pass

    @classmethod
    async def create(
        cls,
        agent_name: str,
        agent_id: int,
        mcp_pool: Optional["MCPPool"] = None,
        model_name: str = "gpt-4o-mini",
    ) -> "DecisionMaker":
        """Create Decision Maker with agent already initialized.

        Args:
            agent_name: Agent name (e.g., "Warren")
            agent_id: Agent ID for tools that need it
            mcp_pool: Optional MCP pool for additional research
            model_name: Model to use (default: gpt-4o-mini)

        Returns:
            DecisionMaker instance with agent ready to use
        """
        instance = cls.__new__(cls)
        instance.agent_name = agent_name
        instance.agent_id = agent_id
        instance.mcp_pool = mcp_pool
        instance.model_name = model_name
        instance.agent = await create_decision_maker_agent(
            agent_name=agent_name,
            agent_id=agent_id,
            mcp_pool=mcp_pool,
            model_name=model_name,
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
            agent_name=context.agent_name,
            agent_style=context.agent_style,
            research_response=context.research_response,
            balance=context.balance,
            position_count=context.position_count,
            max_positions=context.max_positions,
            holdings_summary=context.holdings_summary,
            historical_context=context.historical_context,
            force_trade=context.force_trade,
        )

    async def run(self, context: DecisionContext, max_turns: int = 10) -> AgentRunResult[TradingDecision]:
        """Run decision maker agent and return result with full visibility.

        Encapsulates prompt building, agent execution, and response extraction.
        Returns tool errors in result - caller decides how to handle.

        Args:
            context: DecisionContext with typed models
            max_turns: Maximum agent turns (default: 10)

        Returns:
            AgentRunResult containing:
            - output: TradingDecision with action, symbol, quantity, rationale
            - tool_calls: All tool calls made during execution
            - tool_errors: Any tools that returned error responses

        Raises:
            MaxTurnsExceeded: If agent doesn't complete within max_turns

        Usage:
            result = await maker.run(context)
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
            output=result.final_output_as(TradingDecision),
            tool_calls=tool_calls,
            tool_errors=tool_errors,
        )


async def create_decision_maker_agent(
    agent_name: str,
    agent_id: int,
    mcp_pool: Optional["MCPPool"] = None,
    model_name: str = "gpt-4o-mini",
) -> Agent[TradingDecision]:
    """Create Decision Maker agent for decision phase.

    Args:
        agent_name: Agent name (e.g., "Warren")
        agent_id: Agent ID for tools that need it
        mcp_pool: Optional MCP pool for additional research
        model_name: Model to use (default: gpt-4o-mini)

    Returns:
        Agent configured for trading decisions with structured TradingDecision output

    Note:
        Agent personality is loaded from template files (prompts/decision_maker/{agent_name}.txt).
        Uses structured output (output_type=TradingDecision) instead of tool callback.
    """
    # Load instructions from template file
    instructions = load_and_format_prompt(
        "decision_maker",
        agent_name,
        datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
        result = await get_trading_history(agent_id, symbol, days=90)
        # Serialize typed response to JSON for LLM consumption
        return result.model_dump_json()

    # Create account summary tool
    @function_tool
    async def get_account_summary() -> str:
        """Get current account state (balance and holdings).

        Returns:
            JSON string with current balance and holdings
        """
        balance = await _get_balance_raw(agent_id)
        holdings = await _get_holdings_raw(agent_id)

        holdings_list = [
            {
                "symbol": h.symbol,
                "quantity": h.quantity,
                "average_cost": h.average_cost,
                "current_value": h.quantity * getattr(h, "current_price", h.average_cost),
            }
            for h in holdings
        ]

        return json.dumps(
            {
                "balance": balance,
                "position_count": len(holdings),
                "holdings": holdings_list,
            },
            indent=2,
        )

    # Collect tools (no decide_action - using structured output instead)
    tools = [
        get_symbol_trade_history,
        get_account_summary,
    ]

    # Add MCP servers if provided (dict access)
    mcp_servers = []
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
    agent_name: str,
    agent_style: str,
    research_response: ResearchResponse,
    balance: float,
    position_count: int,
    max_positions: int,
    holdings_summary: str,
    historical_context: str,
    force_trade: bool = False,
) -> str:
    """Build the decision prompt for Decision Maker agent.

    Args:
        agent_name: Agent name
        agent_style: Investment style
        research_response: Market Analyst research results
        balance: Available cash balance
        position_count: Current number of positions
        max_positions: Maximum positions allowed (10)
        holdings_summary: Summary of current holdings
        historical_context: Recent trading history
        force_trade: Whether agent MUST make a trade (no HOLD allowed)

    Returns:
        Formatted prompt string
    """
    # Format research candidates
    candidates_text = "\n".join([f"- {candidate}" for candidate in research_response.candidates])

    # Format research sources
    sources_text = "\n".join(
        [f"- {source.title}: {source.url}" for source in research_response.sources]
    )

    prompt = f"""You are {agent_name}, a {agent_style} trader. Time to make your decision.

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

**Your Task:**
1. Evaluate the Market Analyst's candidates
2. Use get_symbol_trade_history() to check past performance
3. Make your decision: BUY, SELL, or HOLD
4. Provide structured output with:
   - action: BUY, SELL, or HOLD
   - symbol: stock ticker (empty for HOLD)
   - quantity: number of shares (0 for HOLD)
   - rationale: brief 1-2 sentence reason
   - portfolioContext: your current portfolio state and how it factors in
   - historicalContext: what your trading history shows for this stock/sector
   - researchSummary: key findings from the Market Analyst research
   - candidateEvaluation: why this stock vs the other candidates
   - finalRationale: your complete reasoning for this decision

Make your decision now."""

    return prompt
