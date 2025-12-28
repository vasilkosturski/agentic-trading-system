#!/usr/bin/env python3
"""
Direct HTTP trading tools - replaces accounts_server.py MCP proxy
Uses OpenAI Agents SDK @function_tool decorator for automatic schema generation
"""

import asyncio
import json
import logging
from agents import function_tool
from typing import Dict, List, Any, Optional

# Import centralized configuration
from config import BACKEND_API_ACCOUNTS, BACKEND_BASE_URL

# Import type-safe models
from models import Holding

# Import unified HTTP client
from http_client import call_backend, BackendAPIError

logger = logging.getLogger(__name__)

# Use centralized configuration
BACKEND_URL = BACKEND_API_ACCOUNTS

async def _call_backend_api(method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Any:
    """Helper to call Java backend API with new REST endpoints.

    New REST endpoints return direct values without ToolResponse wrapper.
    """
    url = f"{BACKEND_URL}{endpoint}"

    try:
        response = await call_backend(method, url, json_data=data)
        # New REST endpoints return direct JSON values
        return response.json()

    except BackendAPIError as e:
        # Already logged by http_client
        raise Exception(str(e)) from e

@function_tool
async def get_balance(agent_id: int) -> float:
    """Get the cash balance of the given account.

    Args:
        agent_id: Backend identifier for the agent

    Returns:
        Current cash balance in USD as a float
    """
    try:
        result = await _call_backend_api("GET", f"/{agent_id}/balance")
        return float(result)
    except Exception as e:
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
        result = await _call_backend_api("GET", f"/{agent_id}/holdings")
        return result
    except Exception as e:
        logger.error(f"Failed to get holdings for agent {agent_id}: {e}")
        raise Exception(f"Failed to get holdings for agent {agent_id}: {str(e)}")

async def buy_shares(
    agent_id: int,
    symbol: str,
    quantity: int,
    runId: Optional[int] = None,
    agent_name: Optional[str] = None
) -> str:
    """Buy shares of a stock.

    IMPORTANT: Maximum 10 positions per agent. If you already hold 10 different stocks,
    you must sell one before buying a new one. Adding to existing positions is allowed.

    Args:
        agent_id: Backend identifier for the agent
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
        quantity: The number of shares to buy (must be positive integer)
        runId: Optional run ID to link this trade to an agent run

    Returns:
        Confirmation message with transaction details

    Raises:
        Exception: If insufficient funds, position limit reached, or invalid symbol
    """
    try:
        result = await _call_backend_api("POST", f"/{agent_id}/trades", {
            "type": "BUY",
            "symbol": symbol,
            "quantity": quantity,
            "runId": runId
        })
        who = agent_name or agent_id
        logger.info(f"{who} bought {quantity} shares of {symbol}")
        return str(result)
    except Exception as e:
        who = agent_name or agent_id
        logger.error(f"Failed to buy shares for {who}: {e}")
        # Re-raise with original error message (includes position limit info)
        raise Exception(f"Failed to buy {quantity} shares of {symbol}: {str(e)}")

async def sell_shares(
    agent_id: int,
    symbol: str,
    quantity: int,
    runId: Optional[int] = None,
    agent_name: Optional[str] = None
) -> str:
    """Sell shares of a stock.

    Args:
        agent_id: Backend identifier for the agent
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
        quantity: The number of shares to sell (must be positive and ≤ current holdings)
        runId: Optional run ID to link this trade to an agent run

    Returns:
        Confirmation message with transaction details

    Raises:
        Exception: If you don't own enough shares or invalid symbol
    """
    try:
        result = await _call_backend_api("POST", f"/{agent_id}/trades", {
            "type": "SELL",
            "symbol": symbol,
            "quantity": quantity,
            "runId": runId
        })
        who = agent_name or agent_id
        logger.info(f"{who} sold {quantity} shares of {symbol}")
        return str(result)
    except Exception as e:
        who = agent_name or agent_id
        logger.error(f"Failed to sell shares for {who}: {e}")
        raise Exception(f"Failed to sell {quantity} shares of {symbol}: {str(e)}")

async def initialize_agent(name: str, initial_balance: float = 100000.0) -> str:
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
        result = await _call_backend_api("POST", "", {
            "agentName": name,
            "initialBalance": initial_balance
        })
        logger.info(f"Agent {name} initialized with ${initial_balance:,.2f}")
        return f"Agent {name} initialized successfully with ${initial_balance:,.2f}"
    except Exception as e:
        logger.error(f"Failed to initialize agent {name}: {e}")
        raise Exception(f"Failed to initialize agent {name}: {str(e)}")

# Helper functions for system use (not agent tools)

async def _get_balance_raw(agent_id: int) -> float:
    """Raw balance getter - for system use, not exposed to agents"""
    result = await _call_backend_api("GET", f"/{agent_id}/balance")
    return float(result)

async def _get_holdings_raw(agent_id: int) -> List[Holding]:
    """Raw holdings getter - for system use, not exposed to agents.

    Returns:
        List of Holding objects with symbol, quantity, averagePrice
    """
    result = await _call_backend_api("GET", f"/{agent_id}/holdings")
    # Validate at API boundary using Pydantic
    return [Holding(**item) for item in result]

async def get_account_report(agent_id: int) -> str:
    """Get detailed account report - called by system, not exposed as agent tool"""
    try:
        url = f"{BACKEND_BASE_URL}/api/accounts/resources/accounts/{agent_id}"
        response = await call_backend("GET", url)
        return response.text
    except BackendAPIError as e:
        logger.error(f"Failed to get account report for agent {agent_id}: {e}")
        raise Exception(str(e)) from e

# No model-visible trading tools are exported. Account context is provided explicitly
# by the orchestrator; trading actions are dispatched by code, not by the model.
