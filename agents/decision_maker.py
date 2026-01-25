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
from memory_tools import get_trading_history, get_recent_activity

# Import prompt loader
from prompt_loader import load_and_format_prompt

if TYPE_CHECKING:
    from agent_executor import AgentExecutor
    from mcp_types import MCPPool

logger = logging.getLogger(__name__)


async def create_decision_maker_agent(
    agent_name: str,
    executor: "AgentExecutor",
    mcp_pool: Optional["MCPPool"] = None,
    model_name: str = "gpt-4o-mini",
) -> Agent:
    """Create Decision Maker agent for decision phase.

    Args:
        agent_name: Agent name (e.g., "Warren")
        executor: AgentExecutor instance for decision storage
        mcp_pool: Optional MCP pool for additional research
        model_name: Model to use (default: gpt-4o-mini)

    Returns:
        Agent configured for trading decisions
    
    Note:
        Agent personality is loaded from template files (prompts/decision_maker/{agent_name}.txt).
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
        result = await get_trading_history(agent_name, symbol, days=90)
        return result

    # Create account summary tool
    @function_tool
    async def get_account_summary() -> str:
        """Get current account state (balance and holdings).

        Returns:
            JSON string with current balance and holdings
        """
        from agent_executor import AgentExecutor  # Local import to avoid circular

        balance = await _get_balance_raw(executor.agent_id)
        holdings = await _get_holdings_raw(executor.agent_id)

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

    # Create decide_action tool that stores decision in executor
    @function_tool
    async def decide_action(
        action: str,
        symbol: Optional[str] = None,
        quantity: Optional[int] = None,
        rationale: Optional[str] = None,
        fullReasoning: Optional[str] = None,
        researchSources: Optional[str] = None,
        historicalContext: Optional[str] = None,
    ) -> str:
        """Record your trading decision.

        Args:
            action: "BUY", "SELL", or "HOLD"
            symbol: Stock symbol (required for BUY/SELL)
            quantity: Number of shares (required for BUY/SELL)
            rationale: Brief 1-2 sentence reason
            fullReasoning: Complete analysis and reasoning
            researchSources: JSON string with research sources
            historicalContext: JSON string with historical insights

        Returns:
            Confirmation message
        """
        act = (action or "").upper()

        if act not in ("BUY", "SELL", "HOLD"):
            raise ValueError(f"action must be BUY, SELL, or HOLD (got: {action})")

        if act in ("BUY", "SELL"):
            if not symbol or not quantity or quantity <= 0:
                raise ValueError(f"{act} requires symbol and positive quantity")

        # Create and validate decision
        decision = TradingDecision(
            action=act,  # type: ignore
            symbol=symbol or "",
            quantity=quantity or 0,
            rationale=rationale or "",
            fullReasoning=fullReasoning or "",
            researchSources=researchSources or "[]",
            historicalContext=historicalContext or "[]",
        )

        # Validate consistency
        decision.validate_consistency()

        # Store in executor
        executor._pending_decision = decision

        logger.info(f"✅ Decision recorded: {act} {symbol or ''} {quantity or ''}")

        return f"Decision recorded: {act}" + (
            f" {quantity} shares of {symbol}" if act in ("BUY", "SELL") else ""
        )

    # Collect tools
    tools = [
        get_symbol_trade_history,
        get_account_summary,
        decide_action,
    ]

    # Add MCP servers if provided
    mcp_servers = []
    if mcp_pool:
        # Add Brave Search for additional research
        brave_server = await mcp_pool.get_server("brave-search")
        if brave_server:
            mcp_servers.append(brave_server)

        # Add Fetch for web content
        fetch_server = await mcp_pool.get_server("fetch")
        if fetch_server:
            mcp_servers.append(fetch_server)

    # Create agent
    trader = Agent(
        name=f"{agent_name}-DecisionMaker",
        instructions=instructions,
        model=model_name,
        tools=tools,
        mcp_servers=mcp_servers,
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
4. Call decide_action() with your decision and reasoning

Make your decision now."""

    return prompt
