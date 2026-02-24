#!/usr/bin/env python3
"""
Memory tools for agents to query their past trading decisions and reasoning.

These tools allow agents to:
1. Review trading history for specific stocks (trades + run context)
2. See recent activity across all stocks (run-by-run view)

Data sources:
- trading.account_transactions (individual trades)
- analytics.agent_runs (overall cycle reasoning, including non-trades)

API Design:
- All functions use agent_id (integer) as the primary identifier
- Functions return typed Pydantic models (not raw JSON strings)
- Callers serialize to JSON only at boundaries (LLM prompts)
"""

import logging
from config import BACKEND_BASE_URL

# Import unified HTTP client
from http_client import call_backend, BackendAPIError

# Import typed response models
from models.api_responses import (
    RecentActivityResponse,
    SymbolHistoryResponse,
)

logger = logging.getLogger(__name__)


async def get_trading_history(
    agent_id: int, symbol: str, days: int = 30
) -> SymbolHistoryResponse:
    """
    Get complete trading history for a specific stock, including:
    - All trades (BUY/SELL) with reasoning
    - Run context (market conditions, overall strategy)
    - Non-trades (considered but didn't act)

    Args:
        agent_id: Agent ID (integer)
        symbol: Stock symbol (e.g., "NVDA")
        days: How many days back to look (default 30)

    Returns:
        SymbolHistoryResponse with typed trading history

    Raises:
        BackendAPIError: If API call fails
    """
    url = f"{BACKEND_BASE_URL}/api/memory/trading-history"
    params = {
        "agentId": agent_id,
        "symbol": symbol,
        "days": days
    }

    response = await call_backend("GET", url, params=params)
    return SymbolHistoryResponse.model_validate_json(response.text)


async def get_recent_activity(
    agent_id: int, days: int = 7
) -> RecentActivityResponse:
    """
    Get recent trading activity across all stocks, organized by run.
    Shows what the agent has been doing, thinking, and considering.

    Args:
        agent_id: Agent ID (integer)
        days: How many days back to look (default 7)

    Returns:
        RecentActivityResponse with typed activity data

    Raises:
        BackendAPIError: If API call fails
    """
    url = f"{BACKEND_BASE_URL}/api/memory/recent-activity"
    params = {
        "agentId": agent_id,
        "days": days
    }

    response = await call_backend("GET", url, params=params)
    return RecentActivityResponse.model_validate_json(response.text)


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

