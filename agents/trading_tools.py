#!/usr/bin/env python3
"""
Direct HTTP trading helpers - replaces accounts_server.py MCP proxy.

Trading actions (buy/sell/initialize) are dispatched by code, not by the model.
No model-visible @function_tool exports live here; see W5 cleanup notes.
"""

import logging
from typing import List

from backend_client import get_backend_client
from models import Holding, TradeResult
from models.api_responses import AccountReport

logger = logging.getLogger(__name__)


async def buy_shares(
    agent_id: int,
    symbol: str,
    quantity: int,
    runId: int | None = None,
    agent_name: str | None = None
) -> TradeResult:
    """Buy shares of a stock.

    IMPORTANT: Maximum 10 positions per agent. If you already hold 10 different stocks,
    you must sell one before buying a new one. Adding to existing positions is allowed.

    Args:
        agent_id: Backend identifier for the agent
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
        quantity: The number of shares to buy (must be positive integer)
        runId: Optional run ID to link this trade to an agent run
        agent_name: Optional agent name for logging

    Returns:
        TradeResult with symbol, quantity, price, and newBalance

    Raises:
        Exception: If insufficient funds, position limit reached, or invalid symbol
    """
    who = agent_name or str(agent_id)
    # W4: BackendAPIError propagates with status code intact for the caller
    # (agent_executor / orchestrator) to inspect.
    client = get_backend_client()
    result = await client.buy_shares(agent_id, symbol, quantity, run_id=runId)
    logger.info(f"{who} bought {quantity} shares of {symbol}")
    return result


async def sell_shares(
    agent_id: int,
    symbol: str,
    quantity: int,
    runId: int | None = None,
    agent_name: str | None = None
) -> TradeResult:
    """Sell shares of a stock.

    Args:
        agent_id: Backend identifier for the agent
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
        quantity: The number of shares to sell (must be positive and ≤ current holdings)
        runId: Optional run ID to link this trade to an agent run
        agent_name: Optional agent name for logging

    Returns:
        TradeResult with symbol, quantity, price, and newBalance

    Raises:
        Exception: If you don't own enough shares or invalid symbol
    """
    who = agent_name or str(agent_id)
    # W4: BackendAPIError propagates with status code intact (see buy_shares).
    client = get_backend_client()
    result = await client.sell_shares(agent_id, symbol, quantity, run_id=runId)
    logger.info(f"{who} sold {quantity} shares of {symbol}")
    return result


async def initialize_agent(name: str, initial_balance: float = 100000.0) -> int:
    """Initialize agent account if it doesn't exist.

    This is idempotent - safe to call multiple times. If account exists, does nothing.

    NOTE: This is NOT a function_tool - it's called internally by the system, not by agents.

    Args:
        name: The name of the agent (Warren, George, Ray, Cathie)
        initial_balance: Starting balance in USD (defaults to $100,000)

    Returns:
        Confirmation message
    """
    # W4: BackendAPIError propagates with status code intact (see buy_shares).
    client = get_backend_client()
    return await client.initialize_agent(name, initial_balance)


# Helper functions for system use (not agent tools)

async def _get_account_report_raw(agent_id: int) -> AccountReport:
    """Get full account report from backend.

    Returns the typed AccountReport with balance, holdings,
    portfolio metrics, and P&L data in a single HTTP call.
    """
    client = get_backend_client()
    return await client.get_account_report(agent_id)


async def _get_balance_raw(agent_id: int) -> float:
    """Get agent balance from account report - for system use, not exposed to agents."""
    report = await _get_account_report_raw(agent_id)
    return report.balance


async def _get_holdings_raw(agent_id: int) -> List[Holding]:
    """Get agent holdings from account report - for system use, not exposed to agents.

    Returns:
        List of Holding objects with symbol, quantity, averagePrice
    """
    report = await _get_account_report_raw(agent_id)
    return report.holdings


# No model-visible trading tools are exported. Account context is provided explicitly
# by the orchestrator; trading actions are dispatched by code, not by the model.
