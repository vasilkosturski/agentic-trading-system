"""Decision Maker Agent - Decision Phase

This agent runs during the DECIDING phase to evaluate Market Analyst research
and make a BUY/SELL/HOLD decision. Has access to trading tools and can perform
additional research if needed.

Per design document: system-design/workflows/trade-execution/trade_exec_workflow_design.md
"""

import logging
import json
from agents import Agent, function_tool
from datetime import datetime
from typing import Optional, TYPE_CHECKING

# Import models
from models.llm_output import TradingDecision, ResearchResponse

# Import trading and memory tools
from trading_tools import buy_shares, sell_shares, _get_balance_raw, _get_holdings_raw
from memory_tools import get_trading_history

# Import prompt loader
from prompt_loader import load_and_format_prompt

# Import MCP types
from models.mcp_types import MCPServerName

if TYPE_CHECKING:
    from mcp_types import MCPPool

logger = logging.getLogger(__name__)


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

    # Add MCP servers if provided
    mcp_servers = []
    if mcp_pool:
        # Add Brave Search for additional research
        brave_server = await mcp_pool.get_server(MCPServerName.BRAVE_SEARCH)
        if brave_server:
            mcp_servers.append(brave_server)

        # Add Fetch for web content
        fetch_server = await mcp_pool.get_server(MCPServerName.FETCH)
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
4. Provide your structured output with action, symbol, quantity, rationale, and fullReasoning

Make your decision now."""

    return prompt
