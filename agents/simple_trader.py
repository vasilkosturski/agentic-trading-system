#!/usr/bin/env python3
"""
SimpleTrader - Functional approach matching researcher.py pattern

Logic lives in module-level functions, SimpleTrader is a thin config holder
with a run() interface for TradingSystem compatibility.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from textwrap import dedent
from typing import Dict, Optional, Literal, cast

from agents import Agent, trace
from agents import function_tool

from market_tools import MARKET_TOOLS
from memory_tools import get_trading_history, get_recent_activity
from researcher import create_researcher_agent, REQUIRED_MCPS as RESEARCHER_MCPS
from agent_executor import AgentExecutor
from mcp_types import MCPName, MCPPool

logger = logging.getLogger(__name__)


# =============================================================================
# MCP Requirements - Declare what this agent needs
# =============================================================================

# SimpleTrader uses Researcher, which needs these MCPs
REQUIRED_MCPS = RESEARCHER_MCPS


# ============================================================================
# Module-level functions (like researcher.py)
# ============================================================================

def get_trader_instructions(name: str, strategy: str) -> str:
    """Get trader system prompt - defines identity, tools, and rules.
    
    Args:
        name: Agent name (e.g., "Warren")
        strategy: Investment strategy description
        
    Returns:
        System prompt for the trading agent
    """
    return f"""You are {name}, a trader on the stock market. Your account is under your name, {name}.
You actively manage your portfolio according to your strategy.

**YOUR INVESTMENT STRATEGY:**
{strategy}

**AVAILABLE TOOLS:**
- Researcher: Research online for news and opportunities (returns JSON with summary and sources)
- Market data: lookup_share_price, get_historical_prices, get_market_indicators
- Memory: query_trading_history(symbol, days), query_recent_activity(days)

**PORTFOLIO CONSTRAINTS:**
- Maximum 10 positions at any time
- You must sell before buying new positions if at limit
- End-of-day market data from Polygon.io (previous trading day close)

**DECISION WORKFLOW (MANDATORY 3 STEPS):**

⚠️ You MUST call Researcher at least once before deciding. Skipping research will cause an error.

1. **Query History**: Call query_trading_history(symbol, days) for any stock you're considering
   - Build historicalContext JSON: {{"summary": "...", "insights": [{{"date": "...", "insight": "Bought X shares at $Y"}}]}}

2. **Research**: Call Researcher to gather current market information
   - Save the complete JSON response (summary + sources array)

3. **Decide**: Call decide_action() EXACTLY ONCE with:
   - action: "BUY", "SELL", or "HOLD"
   - symbol, quantity (for BUY/SELL)
   - rationale: Brief 1-2 sentence reason
   - fullReasoning: Complete analysis (2-5 paragraphs), CITE sources by title
   - researchSources: Complete JSON from Researcher
   - historicalContext: JSON from your history analysis

**IMPORTANT:**
- Action must match reasoning (don't say "sell" if action="BUY")
- Be CONCRETE in historicalContext - say "Bought 50 NVDA at $145" not "entered a tech position"
- The system executes your decision; do NOT call trading tools directly
"""


def _build_trading_message(
    trader: 'SimpleTrader',
    historical_context: str,
    force_trade: bool
) -> str:
    """Build user message for this trading cycle (internal helper).

    Args:
        trader: SimpleTrader config
        historical_context: Pre-fetched trading history JSON
        force_trade: If True, agent must make BUY/SELL (no HOLD)

    Returns:
        User message for this cycle
    """
    force_instruction = ""
    if force_trade:
        force_instruction = dedent("""
            🎯 **MANUAL TRIGGER - ACTION REQUIRED**
            You MUST make a trade (BUY or SELL) this cycle. HOLD is NOT allowed.
            Choose your best opportunity - either buy a new position or sell an existing one.

        """)

    history_section = ""
    if historical_context:
        history_section = f"\n**YOUR RECENT TRADING HISTORY:**\n{historical_context}\n"

    return f"""{force_instruction}Conduct your portfolio review.

Current time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
{history_section}
Review your holdings, research opportunities, and make your decision.
"""


async def create_trader_agent(
    trader: 'SimpleTrader',
    mcp_pool: MCPPool,
    executor: AgentExecutor
) -> Agent:
    """Create agent with all tools.

    Args:
        trader: SimpleTrader config with name, strategy, model_name
        mcp_pool: MCP pool - passed to researcher
        executor: AgentExecutor instance for decision storage

    Returns:
        Agent instance ready to run
    """
    # Create researcher agent and wrap as tool
    researcher_agent = await create_researcher_agent(mcp_pool, trader.model_name)
    researcher_tool = researcher_agent.as_tool(
        tool_name="Researcher",
        tool_description="Research online for news and opportunities. "
        "Describe what you're looking for - can research specific stocks, "
        "market conditions, or general financial news. "
        "Returns JSON with summary and sources."
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
        """Record your trading decision with research sources and historical context.

        ⚠️ CRITICAL: You MUST call Researcher before calling this function.
        """
        # ENFORCEMENT: Check if research was conducted
        if not executor.tracker or not executor.tracker.research_queries:
            raise ValueError(
                "❌ RESEARCH REQUIRED: You must call Researcher at least once before making decisions.\n"
                "Markets change constantly - always gather current information first.\n"
                "Call researcher() with your portfolio context before deciding.\n\n"
                "Example: researcher('I am Warren. Review my holdings and check for news on each position')"
            )

        act = (action or "").upper()

        # CRITICAL DEBUG: Log what agent is passing
        logger.error(f"🔴 DECIDE_ACTION CALLED: action={action}, symbol={symbol}, quantity={quantity}")
        logger.error(f"🔴 DECIDE_ACTION RATIONALE: {rationale[:200] if rationale else 'None'}")

        # VALIDATION: Check if action matches reasoning
        if act in ("BUY", "SELL"):
            if not symbol or not isinstance(quantity, int) or quantity <= 0:
                raise ValueError("symbol and positive quantity are required for BUY/SELL")

            reasoning_text = (rationale or "") + " " + (fullReasoning or "")
            reasoning_lower = reasoning_text.lower()

            if act == "BUY" and ("sell" in reasoning_lower or "selling" in reasoning_lower):
                rationale_excerpt = (rationale or "")[:100]
                error_msg = f"CRITICAL ERROR: action=BUY but reasoning mentions 'sell'. Reasoning: {rationale_excerpt}"
                logger.error(f"🚨 {error_msg}")
                raise ValueError(error_msg)

            if act == "SELL" and ("buy" in reasoning_lower or "buying" in reasoning_lower):
                rationale_excerpt = (rationale or "")[:100]
                error_msg = f"CRITICAL ERROR: action=SELL but reasoning mentions 'buy'. Reasoning: {rationale_excerpt}"
                logger.error(f"🚨 {error_msg}")
                raise ValueError(error_msg)
        else:
            act = "HOLD"
            symbol = symbol or ""
            quantity = quantity or 0

        # Store decision in executor
        executor.store_decision(
            action=cast(Literal["BUY", "SELL", "HOLD"], act),
            symbol=symbol,
            quantity=quantity,
            rationale=rationale or "",
            full_reasoning=fullReasoning or "",
            research_sources=researchSources or "[]",
            historical_context=historicalContext or "[]",
        )

        return "Decision recorded. The system will validate and execute this trade."

    # Create memory query tools
    @function_tool
    async def query_trading_history(symbol: str, days: int = 30) -> str:
        """Get your complete trading history for a specific stock."""
        result = await get_trading_history(trader.name, symbol, days)
        if executor.tracker and result:
            summary = result[:150] + "..." if len(result) > 150 else result
            executor.tracker.log_data_access(f"Trading History ({symbol})", summary)
        return result

    @function_tool
    async def query_recent_activity(days: int = 7) -> str:
        """Get your recent trading activity across all stocks."""
        result = await get_recent_activity(trader.name, days)
        if executor.tracker and result:
            summary = result[:150] + "..." if len(result) > 150 else result
            executor.tracker.log_data_access(f"Recent Activity ({days}d)", summary)
        return result

    # Combine all tools
    all_tools = [
        researcher_tool,
        *MARKET_TOOLS,
        decide_action,
        query_trading_history,
        query_recent_activity,
    ]

    return Agent(
        name=trader.name,
        instructions=get_trader_instructions(trader.name, trader.strategy),
        model=trader.model_name,
        tools=all_tools,
    )


async def run_trader_cycle(trader: 'SimpleTrader', mcp_pool: MCPPool, force_trade: bool = False):
    """Run a complete trading cycle for an agent.

    Args:
        trader: SimpleTrader config
        mcp_pool: MCP pool - agent selects servers from REQUIRED_MCPS
        force_trade: If True, agent MUST make a BUY or SELL trade (no HOLD)
    """
    try:
        logger.info(f"Starting {trader.name} agent...")
        if force_trade:
            logger.info(f"🎯 {trader.name} must make a trade this cycle (manual trigger)")

        # Setup tracing
        trace_name = f"{trader.name}-portfolio-review"
        trace_id = f"trace_{trader.name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        with trace(trace_name, trace_id=trace_id):
            # Create executor for this cycle
            executor = AgentExecutor(trader.agent_id, trader.name, trader.strategy)

            # Create callable wrappers for executor
            def build_message_fn(historical_context: str, force_trade_flag: bool) -> str:
                return _build_trading_message(trader, historical_context, force_trade_flag)

            async def create_agent_fn(exec: AgentExecutor) -> Agent:
                return await create_trader_agent(trader, mcp_pool, exec)

            # Execute the trading cycle
            await executor.execute_cycle(
                build_message_fn=build_message_fn,
                create_agent_fn=create_agent_fn,
                force_trade=force_trade,
            )

        logger.info(f"{trader.name} agent completed successfully")

    except Exception as e:
        logger.error(f"Error running {trader.name} agent: {e}", exc_info=True)


# ============================================================================
# Config class (thin wrapper for TradingSystem compatibility)
# ============================================================================

@dataclass
class SimpleTrader:
    """Config holder with run interface for TradingSystem compatibility.

    This is intentionally minimal - all logic lives in module-level functions
    to match the researcher.py pattern.
    """
    name: str
    strategy: str
    model_name: str = "gpt-4o-mini"
    agent_id: Optional[int] = None

    async def run(self, mcp_pool: MCPPool, force_trade: bool = False):
        """Run a trading cycle. Delegates to module-level function.

        Args:
            mcp_pool: MCP pool with servers this agent needs
            force_trade: If True, agent MUST make a trade (no HOLD)
        """
        await run_trader_cycle(self, mcp_pool, force_trade)
