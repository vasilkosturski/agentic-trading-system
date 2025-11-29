#!/usr/bin/env python3
"""
Direct HTTP trading tools - replaces accounts_server.py MCP proxy
Uses OpenAI Agents SDK @function_tool decorator for automatic schema generation
"""

import aiohttp
import asyncio
import json
import logging
from agents import function_tool
from typing import Dict

# Import centralized configuration
from config import BACKEND_API_ACCOUNTS, BACKEND_BASE_URL

logger = logging.getLogger(__name__)

# Use centralized configuration
BACKEND_URL = BACKEND_API_ACCOUNTS

async def _call_backend_api(endpoint: str, data: dict = None) -> any:
    """Helper to call Java backend API"""
    url = f"{BACKEND_URL}{endpoint}"
    timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            if data:
                logger.debug(f"POST {url} with data: {data}")
                async with session.post(url, json=data) as response:
                    response_text = await response.text()
                    logger.debug(f"Response status: {response.status}, body: {response_text}")

                    try:
                        result = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response from {url}: {response_text}")
                        raise Exception(f"Invalid JSON response from API: {str(e)}")

                    # Accept both 200 (OK) and 201 (Created) as success
                    if response.status in [200, 201] and result.get("success"):
                        return result.get("data")
                    else:
                        error_msg = result.get("error") or f"HTTP {response.status}"
                        logger.error(f"API call failed: {error_msg}, response: {result}")
                        raise Exception(f"API call failed: {error_msg}")
            else:
                logger.debug(f"GET {url}")
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        response_text = await response.text()
                        logger.error(f"GET failed with status {response.status}: {response_text}")
                        raise Exception(f"API call failed with status {response.status}")
    except aiohttp.ClientError as e:
        logger.error(f"Network error calling {url}: {type(e).__name__}: {str(e)}")
        raise Exception(f"Network error: {str(e)}")
    except asyncio.TimeoutError:
        logger.error(f"Timeout calling {url} after 30 seconds")
        raise Exception(f"Request timeout after 30 seconds")

@function_tool
async def get_balance(agent_id: int) -> float:
    """Get the cash balance of the given account.

    Args:
        agent_id: Backend identifier for the agent

    Returns:
        Current cash balance in USD as a float
    """
    try:
        result = await _call_backend_api("/tools/get_balance", {"agentId": agent_id})
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
        result = await _call_backend_api("/tools/get_holdings", {"agentId": agent_id})
        return result
    except Exception as e:
        logger.error(f"Failed to get holdings for agent {agent_id}: {e}")
        raise Exception(f"Failed to get holdings for agent {agent_id}: {str(e)}")

async def buy_shares(
    agent_id: int,
    symbol: str,
    quantity: int,
    rationale: str,
    fullReasoning: str = None,
    researchSources: str = None,
    historicalContext: str = None,
    agentContext: str = None,
    runId: int = None,
    agent_name: str | None = None
) -> str:
    """Buy shares of a stock.

    IMPORTANT: Maximum 10 positions per agent. If you already hold 10 different stocks,
    you must sell one before buying a new one. Adding to existing positions is allowed.

    Args:
        agent_id: Backend identifier for the agent
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
        historicalContext: (RECOMMENDED) JSON string with historical insights from past trades.
            Example: '{"summary": "...", "insights": [{"date": "...", "insight": "..."}]}'
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
                balance = await _get_balance_raw(agent_id)
                holdings = await _get_holdings_raw(agent_id)
                agentContext = json.dumps({
                    "cashBefore": balance,
                    "positionsBefore": len(holdings),
                    "holdingsBefore": holdings
                })
            except Exception as ctx_err:
                logger.warning(f"Failed to capture agent context: {ctx_err}")

        result = await _call_backend_api("/tools/buy_shares", {
            "agentId": agent_id,
            "symbol": symbol,
            "quantity": quantity,
            "rationale": rationale,
            "fullReasoning": fullReasoning,
            "researchSources": researchSources,
            "historicalContext": historicalContext,
            "agentContext": agentContext,
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
    rationale: str,
    fullReasoning: str = None,
    researchSources: str = None,
    historicalContext: str = None,
    agentContext: str = None,
    runId: int = None,
    agent_name: str | None = None
) -> str:
    """Sell shares of a stock.

    Args:
        agent_id: Backend identifier for the agent
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
        historicalContext: (RECOMMENDED) JSON string with historical insights from past trades.
            Example: '{"summary": "...", "insights": [{"date": "...", "insight": "..."}]}'
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
                balance = await _get_balance_raw(agent_id)
                holdings = await _get_holdings_raw(agent_id)
                agentContext = json.dumps({
                    "cashBefore": balance,
                    "positionsBefore": len(holdings),
                    "holdingsBefore": holdings
                })
            except Exception as ctx_err:
                logger.warning(f"Failed to capture agent context: {ctx_err}")

        result = await _call_backend_api("/tools/sell_shares", {
            "agentId": agent_id,
            "symbol": symbol,
            "quantity": quantity,
            "rationale": rationale,
            "fullReasoning": fullReasoning,
            "researchSources": researchSources,
            "historicalContext": historicalContext,
            "agentContext": agentContext,
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

async def _get_balance_raw(agent_id: int) -> float:
    """Raw balance getter - for system use, not exposed to agents"""
    result = await _call_backend_api("/tools/get_balance", {"agentId": agent_id})
    return float(result)

async def _get_holdings_raw(agent_id: int) -> Dict[str, int]:
    """Raw holdings getter - for system use, not exposed to agents"""
    result = await _call_backend_api("/tools/get_holdings", {"agentId": agent_id})
    return result

async def get_account_report(agent_id: int) -> str:
    """Get detailed account report - called by system, not exposed as agent tool"""
    try:
        url = f"{BACKEND_BASE_URL}/api/accounts/resources/accounts/{agent_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    raise Exception(f"Failed to get account report: status {response.status}")
    except Exception as e:
        logger.error(f"Failed to get account report for agent {agent_id}: {e}")
        raise

async def get_strategy(name: str) -> str:
    """Get agent strategy - called by system, not exposed as agent tool"""
    try:
        url = f"{BACKEND_BASE_URL}/api/accounts/resources/strategy/{name}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    raise Exception(f"Failed to get strategy: status {response.status}")
    except Exception as e:
        logger.error(f"Failed to get strategy for {name}: {e}")
        raise

# No model-visible trading tools are exported. Account context is provided explicitly
# by the orchestrator; trading actions are dispatched by code, not by the model.
