#!/usr/bin/env python3
"""
Data layer for agent memory/history queries.

Provides typed functions to fetch agent data from the backend API.
Used by MarketAnalyst and other agents that need portfolio context.

Functions:
- _fetch_holdings(agent_id) → HoldingsResponse
- _fetch_recent_activity(agent_id, days) → RecentActivityResponse
- _fetch_symbol_history(agent_id, symbol, days) → SymbolHistoryResponse
- _fetch_price(symbol) → PriceLookupResponse

All functions throw BackendAPIError on failure (no ToolError here -
that's handled at the agent tool layer in market_analyst.py).
"""

from datetime import datetime
from config import BACKEND_BASE_URL
from http_client import call_backend
from models import (
    HoldingsResponse,
    RecentActivityResponse,
    SymbolHistoryResponse,
    PriceLookupResponse,
)


async def _fetch_holdings(agent_id: int) -> HoldingsResponse:
    """Fetch holdings from backend API.

    Args:
        agent_id: ID of the trading agent

    Returns:
        HoldingsResponse with agent's current holdings

    Raises:
        BackendAPIError: If the API call fails
    """
    url = f"{BACKEND_BASE_URL}/api/memory/holdings"
    params = {"agentId": agent_id}
    response = await call_backend("GET", url, params=params)
    return HoldingsResponse.model_validate_json(response.text)


async def _fetch_recent_activity(agent_id: int, days: int) -> RecentActivityResponse:
    """Fetch recent activity from backend API.

    Args:
        agent_id: ID of the trading agent
        days: Number of days to look back

    Returns:
        RecentActivityResponse with recent trading runs

    Raises:
        BackendAPIError: If the API call fails
    """
    url = f"{BACKEND_BASE_URL}/api/memory/recent-activity"
    params = {"agentId": agent_id, "days": days}
    response = await call_backend("GET", url, params=params)
    return RecentActivityResponse.model_validate_json(response.text)


async def _fetch_symbol_history(agent_id: int, symbol: str, days: int) -> SymbolHistoryResponse:
    """Fetch symbol trading history from backend API.

    Args:
        agent_id: ID of the trading agent
        symbol: Stock symbol (e.g., AAPL)
        days: Number of days to look back

    Returns:
        SymbolHistoryResponse with trading history for the symbol

    Raises:
        BackendAPIError: If the API call fails
    """
    url = f"{BACKEND_BASE_URL}/api/memory/trading-history"
    params = {"agentId": agent_id, "symbol": symbol, "days": days}
    response = await call_backend("GET", url, params=params)
    return SymbolHistoryResponse.model_validate_json(response.text)


async def _fetch_price(symbol: str) -> PriceLookupResponse:
    """Fetch current price from market tools.

    Args:
        symbol: Stock symbol (e.g., AAPL)

    Returns:
        PriceLookupResponse with current price

    Raises:
        Exception: If price lookup fails
    """
    from market_tools import _lookup_share_price
    price = await _lookup_share_price(symbol)
    return PriceLookupResponse(
        symbol=symbol,
        price=price,
        timestamp=datetime.now().isoformat()
    )
