#!/usr/bin/env python3
"""
Direct HTTP trading tools - replaces accounts_server.py MCP proxy
Uses OpenAI Agents SDK @function_tool decorator for automatic schema generation
"""

import aiohttp
import json
import logging
from agents import function_tool
from typing import Dict

logger = logging.getLogger(__name__)

# Configuration - Use Docker service name for container networking
BACKEND_URL = "http://backend-service:8080/api/accounts"

async def _call_backend_api(endpoint: str, data: dict = None) -> any:
    """Helper to call Java backend API"""
    url = f"{BACKEND_URL}{endpoint}"

    async with aiohttp.ClientSession() as session:
        if data:
            async with session.post(url, json=data) as response:
                result = await response.json()
                if response.status == 200 and result.get("success"):
                    return result.get("data")
                else:
                    error_msg = result.get("error", "Unknown error")
                    raise Exception(f"API call failed: {error_msg}")
        else:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    raise Exception(f"API call failed with status {response.status}")

@function_tool
async def get_balance(name: str) -> float:
    """Get the cash balance of the given account.

    Args:
        name: The name of the account holder (e.g., 'Warren', 'George', 'Ray', 'Cathie')

    Returns:
        Current cash balance in USD as a float
    """
    try:
        result = await _call_backend_api("/tools/get_balance", {"name": name})
        return float(result)
    except Exception as e:
        logger.error(f"Failed to get balance for {name}: {e}")
        raise Exception(f"Failed to get balance for {name}: {str(e)}")

@function_tool
async def get_holdings(name: str) -> Dict[str, int]:
    """Get the stock holdings of the given account.

    Args:
        name: The name of the account holder

    Returns:
        Dictionary mapping stock symbols to quantities owned
        Example: {'AAPL': 10, 'GOOGL': 5, 'TSLA': 3}
    """
    try:
        result = await _call_backend_api("/tools/get_holdings", {"name": name})
        return result
    except Exception as e:
        logger.error(f"Failed to get holdings for {name}: {e}")
        raise Exception(f"Failed to get holdings for {name}: {str(e)}")

@function_tool
async def buy_shares(
    name: str,
    symbol: str,
    quantity: int,
    rationale: str,
    fullReasoning: str = None,
    researchSources: str = None,
    agentContext: str = None
) -> str:
    """Buy shares of a stock.

    IMPORTANT: Maximum 10 positions per agent. If you already hold 10 different stocks,
    you must sell one before buying a new one. Adding to existing positions is allowed.

    Args:
        name: The name of the account holder
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
        quantity: The number of shares to buy (must be positive integer)
        rationale: Brief explanation of the trade (1-2 sentences)
        fullReasoning: (RECOMMENDED) Detailed explanation including:
            - Why this stock fits your strategy
            - Key research findings that informed your decision
            - Risk assessment and conviction level
            - How this fits with your existing portfolio
        researchSources: (RECOMMENDED) JSON string with array of sources consulted.
            Example: '[{"title": "Article Title", "url": "https://...", "snippet": "key quote"}]'
        agentContext: (RECOMMENDED) JSON string with portfolio state before trade.
            Example: '{"cashBefore": 50000, "portfolioValue": 100000, "positionCount": 5}'

    Returns:
        Confirmation message with transaction details

    Raises:
        Exception: If insufficient funds, position limit reached, or invalid symbol
    """
    try:
        # Capture current portfolio state if not provided
        if agentContext is None:
            try:
                balance = await _call_backend_api("/tools/get_balance", {"name": name})
                holdings = await _call_backend_api("/tools/get_holdings", {"name": name})
                agentContext = json.dumps({
                    "cashBefore": float(balance),
                    "positionsBefore": len(holdings),
                    "holdingsBefore": holdings
                })
            except Exception as ctx_err:
                logger.warning(f"Failed to capture agent context: {ctx_err}")

        result = await _call_backend_api("/tools/buy_shares", {
            "name": name,
            "symbol": symbol,
            "quantity": quantity,
            "rationale": rationale,
            "fullReasoning": fullReasoning,
            "researchSources": researchSources,
            "agentContext": agentContext
        })
        logger.info(f"{name} bought {quantity} shares of {symbol}")
        return str(result)
    except Exception as e:
        logger.error(f"Failed to buy shares for {name}: {e}")
        # Re-raise with original error message (includes position limit info)
        raise Exception(f"Failed to buy {quantity} shares of {symbol}: {str(e)}")

@function_tool
async def sell_shares(
    name: str,
    symbol: str,
    quantity: int,
    rationale: str,
    fullReasoning: str = None,
    researchSources: str = None,
    agentContext: str = None
) -> str:
    """Sell shares of a stock.

    Args:
        name: The name of the account holder
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
        quantity: The number of shares to sell (must be positive and ≤ current holdings)
        rationale: Brief explanation of the trade (1-2 sentences)
        fullReasoning: (RECOMMENDED) Detailed explanation including:
            - Why you're exiting/reducing this position
            - What changed in your thesis or market conditions
            - Risk assessment and timing rationale
            - Impact on portfolio allocation
        researchSources: (RECOMMENDED) JSON string with array of sources consulted.
            Example: '[{"title": "Article Title", "url": "https://...", "snippet": "key quote"}]'
        agentContext: (RECOMMENDED) JSON string with portfolio state before trade.
            Example: '{"cashBefore": 50000, "portfolioValue": 100000, "positionCount": 5}'

    Returns:
        Confirmation message with transaction details

    Raises:
        Exception: If you don't own enough shares or invalid symbol
    """
    try:
        # Capture current portfolio state if not provided
        if agentContext is None:
            try:
                balance = await _call_backend_api("/tools/get_balance", {"name": name})
                holdings = await _call_backend_api("/tools/get_holdings", {"name": name})
                agentContext = json.dumps({
                    "cashBefore": float(balance),
                    "positionsBefore": len(holdings),
                    "holdingsBefore": holdings
                })
            except Exception as ctx_err:
                logger.warning(f"Failed to capture agent context: {ctx_err}")

        result = await _call_backend_api("/tools/sell_shares", {
            "name": name,
            "symbol": symbol,
            "quantity": quantity,
            "rationale": rationale,
            "fullReasoning": fullReasoning,
            "researchSources": researchSources,
            "agentContext": agentContext
        })
        logger.info(f"{name} sold {quantity} shares of {symbol}")
        return str(result)
    except Exception as e:
        logger.error(f"Failed to sell shares for {name}: {e}")
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
        result = await _call_backend_api("/tools/initialize_agent", {
            "name": name,
            "initialBalance": initial_balance
        })
        logger.info(f"Agent {name} initialized with ${initial_balance:,.2f}")
        return f"Agent {name} initialized successfully with ${initial_balance:,.2f}"
    except Exception as e:
        logger.error(f"Failed to initialize agent {name}: {e}")
        raise Exception(f"Failed to initialize agent {name}: {str(e)}")

# Helper functions for system use (not agent tools)

async def get_account_report(name: str) -> str:
    """Get detailed account report - called by system, not exposed as agent tool"""
    try:
        url = f"http://backend-service:8080/api/accounts/resources/accounts/{name}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    raise Exception(f"Failed to get account report: status {response.status}")
    except Exception as e:
        logger.error(f"Failed to get account report for {name}: {e}")
        raise

async def get_strategy(name: str) -> str:
    """Get agent strategy - called by system, not exposed as agent tool"""
    try:
        url = f"http://backend-service:8080/api/accounts/resources/strategy/{name}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    raise Exception(f"Failed to get strategy: status {response.status}")
    except Exception as e:
        logger.error(f"Failed to get strategy for {name}: {e}")
        raise

# All trading tools that agents can use
# NOTE: initialize_agent is NOT included - it's called by the system, not agents
TRADING_TOOLS = [
    get_balance,
    get_holdings,
    buy_shares,
    sell_shares,
]
