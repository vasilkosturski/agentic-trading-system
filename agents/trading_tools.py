#!/usr/bin/env python3
"""
Direct HTTP trading tools - replaces accounts_server.py MCP proxy
Uses OpenAI Agents SDK @function_tool decorator for automatic schema generation
"""

import logging
from agents import function_tool
from typing import Dict, List, Optional

from backend_client import get_backend_client, BackendAPIError
from models import Holding, TradeResult
from models.api_responses import AccountReport

logger = logging.getLogger(__name__)


@function_tool
async def get_balance(agent_id: int) -> float:
    """Get the cash balance of the given account.

    Args:
        agent_id: Backend identifier for the agent

    Returns:
        Current cash balance in USD as a float
    """
    try:
        return await _get_balance_raw(agent_id)
    except BackendAPIError as e:
        logger.error(f"Failed to get balance for agent {agent_id}: {e}")
        raise Exception(f"Failed to get balance for agent {agent_id}: {str(e)}")


@function_tool
async def get_holdings(agent_id: int) -> Dict[str, int]:
    """Get the stock holdings of the given account.

    Args:
        agent_id: Backend identifier for the agent

    Returns:
        Dictionary mapping stock symbols to quantities owned
        Example: {'AAPL': 10, 'GOOGL': 5, 'TSLA': 3}
    """
    try:
        holdings = await _get_holdings_raw(agent_id)
        return {h.symbol: h.quantity for h in holdings}
    except BackendAPIError as e:
        logger.error(f"Failed to get holdings for agent {agent_id}: {e}")
        raise Exception(f"Failed to get holdings for agent {agent_id}: {str(e)}")


async def buy_shares(
    agent_id: int,
    symbol: str,
    quantity: int,
    runId: Optional[int] = None,
    agent_name: Optional[str] = None
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
    try:
        client = get_backend_client()
        result = await client.buy_shares(agent_id, symbol, quantity, run_id=runId)
        logger.info(f"{who} bought {quantity} shares of {symbol}")
        return result
    except BackendAPIError as e:
        logger.error(f"Failed to buy shares for {who}: {e}")
        raise Exception(f"Failed to buy {quantity} shares of {symbol}: {str(e)}")


async def sell_shares(
    agent_id: int,
    symbol: str,
    quantity: int,
    runId: Optional[int] = None,
    agent_name: Optional[str] = None
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
    try:
        client = get_backend_client()
        result = await client.sell_shares(agent_id, symbol, quantity, run_id=runId)
        logger.info(f"{who} sold {quantity} shares of {symbol}")
        return result
    except BackendAPIError as e:
        logger.error(f"Failed to sell shares for {who}: {e}")
        raise Exception(f"Failed to sell {quantity} shares of {symbol}: {str(e)}")


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
    try:
        client = get_backend_client()
        return await client.initialize_agent(name, initial_balance)
    except BackendAPIError as e:
        logger.error(f"Failed to initialize agent {name}: {e}")
        raise Exception(f"Failed to initialize agent {name}: {str(e)}")


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
