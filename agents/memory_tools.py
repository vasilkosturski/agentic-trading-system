#!/usr/bin/env python3
"""
Memory tools for agents to query their past trading decisions and reasoning.

These tools allow agents to:
1. Review trading history for specific stocks (trades + run context)
2. See recent activity across all stocks (run-by-run view)

Data sources:
- trading.account_transactions (individual trades)
- analytics.agent_runs (overall cycle reasoning, including non-trades)
"""

import logging
from typing import Optional
from config import BACKEND_BASE_URL

# Import unified HTTP client
from http_client import call_backend, BackendAPIError

logger = logging.getLogger(__name__)


async def get_trading_history(agent_name: str, symbol: str, days: int = 30) -> str:
    """
    Get complete trading history for a specific stock, including:
    - All trades (BUY/SELL) with reasoning
    - Run context (market conditions, overall strategy)
    - Non-trades (considered but didn't act)

    Args:
        agent_name: Name of the agent (e.g., "Warren")
        symbol: Stock symbol (e.g., "NVDA")
        days: How many days back to look (default 30)

    Returns:
        Natural language summary of trading history
    """
    try:
        url = f"{BACKEND_BASE_URL}/api/memory/trading-history"
        params = {
            "agentName": agent_name,
            "symbol": symbol,
            "days": days
        }

        response = await call_backend("GET", url, params=params, timeout=10)
        return response.text  # Returns JSON string as-is

    except BackendAPIError as e:
        # Convert HTTP errors to JSON strings (for LLM)
        if e.status_code == 404:
            return '{"error": "No trading history found"}'

        # Log already done by http_client, just return error JSON
        return f'{{"error": "{str(e)}"}}'


async def get_recent_activity(agent_name: str, days: int = 7) -> str:
    """
    Get recent trading activity across all stocks, organized by run.
    Shows what the agent has been doing, thinking, and considering.

    Args:
        agent_name: Name of the agent (e.g., "Warren")
        days: How many days back to look (default 7)

    Returns:
        Natural language summary of recent activity
    """
    try:
        url = f"{BACKEND_BASE_URL}/api/memory/recent-activity"
        params = {
            "agentName": agent_name,
            "days": days
        }

        response = await call_backend("GET", url, params=params, timeout=10)
        return response.text  # Returns JSON string as-is

    except BackendAPIError as e:
        # Convert HTTP errors to JSON strings (for LLM)
        if e.status_code == 404:
            return '{"error": "No recent activity found"}'

        # Log already done by http_client, just return error JSON
        return f'{{"error": "{str(e)}"}}'


# Tool metadata for OpenAI Agents SDK
MEMORY_TOOLS_METADATA = {
    "get_trading_history": {
        "description": (
            "Get your complete trading history for a specific stock. "
            "Shows all trades (BUY/SELL), your reasoning at the time, "
            "market conditions, and times you considered but didn't trade. "
            "Use this to remember your thesis and conviction level for a stock."
        ),
        "parameters": {
            "symbol": "Stock symbol (e.g., 'NVDA', 'AAPL')",
            "days": "How many days back to look (default 30)"
        }
    },
    "get_recent_activity": {
        "description": (
            "Get your recent trading activity across all stocks. "
            "Shows what you've been doing, thinking, and considering in recent runs. "
            "Use this to understand your current portfolio strategy and avoid repetitive trades."
        ),
        "parameters": {
            "days": "How many days back to look (default 7)"
        }
    }
}

