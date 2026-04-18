#!/usr/bin/env python3
"""
SimpleTrader - Functional approach matching researcher.py pattern

Logic lives in module-level functions, SimpleTrader is a thin config holder
with a run() interface for TradingSystem compatibility.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from agents import trace

from agent_executor import AgentExecutor
from config import config
from models.investment_style import InvestmentStyle
from mcp_types import MCPName, MCPPool

logger = logging.getLogger(__name__)


# =============================================================================
# MCP Requirements - Declare what this agent needs
# =============================================================================

# SimpleTrader uses MarketAnalyst which needs Brave Search + Fetch for research
REQUIRED_MCPS = [MCPName.BRAVE_SEARCH, MCPName.FETCH]


# ============================================================================
# Module-level functions (like researcher.py)
# ============================================================================

# ============================================================================
# Old single-agent code deleted - now using two-agent architecture
# - get_trader_instructions() - removed
# - _build_trading_message() - removed
# - create_trader_agent() - removed
# These functions are no longer needed with the Market Analyst + Trader Decision
# two-agent architecture implemented in agent_executor.py
# ============================================================================


async def run_trader_cycle(trader: 'SimpleTrader', mcp_pool: MCPPool, force_trade: bool = False):
    """Run a complete trading cycle with two-agent architecture.

    Args:
        trader: SimpleTrader config
        mcp_pool: MCP pool - used to create Market Analyst and Trader Decision agents
        force_trade: If True, agent MUST make a BUY or SELL trade (no HOLD)
    """
    try:
        logger.info(f"Starting {trader.name} agent with two-agent architecture...")
        if force_trade:
            logger.info(f"🎯 {trader.name} must make a trade this cycle (manual trigger)")

        # Setup tracing
        trace_name = f"{trader.name}-portfolio-review"
        trace_id = f"trace_{trader.name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        with trace(trace_name, trace_id=trace_id):
            # Create executor for this cycle (two-agent architecture)
            # agent_id is required in SimpleTrader dataclass, guaranteed to be set
            executor = AgentExecutor(
                agent_id=trader.agent_id,
                name=trader.name,
                agent_style=trader.agent_style,
                model_name=trader.model_name,
            )

            # Execute the trading cycle (two-agent architecture)
            # Executor will create Market Analyst and Trader Decision agents internally
            await executor.execute_cycle(
                mcp_pool=mcp_pool,
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
    agent_style: InvestmentStyle
    strategy: str
    agent_id: int  # Required - set by TradingSystem.create()
    model_name: str = config.OPENAI_MODEL

    async def run(self, mcp_pool: MCPPool, force_trade: bool = False):
        """Run a trading cycle. Delegates to module-level function.

        Args:
            mcp_pool: MCP pool with servers this agent needs
            force_trade: If True, agent MUST make a trade (no HOLD)
        """
        await run_trader_cycle(self, mcp_pool, force_trade)
