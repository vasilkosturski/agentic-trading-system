#!/usr/bin/env python3
"""
Direct HTTP market data tools - calls consolidated GET /api/market/{symbol} endpoint.
Uses OpenAI Agents SDK @function_tool decorator for automatic schema generation.

All 4 tool functions hit a single backend endpoint. Per-symbol caching with TTL
avoids redundant HTTP calls when the LLM calls multiple tools for the same symbol.
"""

import logging
import time
from agents import function_tool
from typing import Dict, Optional, Tuple

# Import centralized configuration
from config import BACKEND_API_MARKET

# Import unified HTTP client
from http_client import call_backend, BackendAPIError

# Import type-safe models
from models import MarketData, PriceMetadata

logger = logging.getLogger(__name__)

# Use centralized configuration
BACKEND_URL = BACKEND_API_MARKET

# Per-symbol cache: symbol -> (MarketData, fetch_timestamp)
_market_data_cache: Dict[str, Tuple[MarketData, float]] = {}

# Cache TTL in seconds (5 minutes — within a single agent cycle, data doesn't change)
_CACHE_TTL_SECONDS = 300


def _get_cached(symbol: str) -> Optional[MarketData]:
    """Return cached MarketData if present and not expired."""
    upper = symbol.upper()
    entry = _market_data_cache.get(upper)
    if entry is None:
        return None
    data, fetched_at = entry
    if time.monotonic() - fetched_at > _CACHE_TTL_SECONDS:
        del _market_data_cache[upper]
        return None
    return data


def _put_cache(symbol: str, data: MarketData) -> None:
    """Store MarketData in the per-symbol cache."""
    _market_data_cache[symbol.upper()] = (data, time.monotonic())


async def _fetch_market_data(symbol: str, days: int = 30) -> MarketData:
    """Fetch combined market data from the consolidated endpoint.

    Returns cached data if available; otherwise makes a single HTTP call
    and caches the result.
    """
    cached = _get_cached(symbol)
    if cached is not None:
        logger.debug("Cache hit for %s", symbol.upper())
        return cached

    url = f"{BACKEND_URL}/{symbol}?days={days}"
    try:
        response = await call_backend("GET", url)
        data = MarketData(**response.json())
        _put_cache(symbol, data)
        return data
    except BackendAPIError as e:
        raise Exception(str(e)) from e


async def _lookup_share_price(symbol: str) -> float:
    """Internal: Get current price (no decorator).

    Used by other modules that need to call this as a regular function.

    Returns:
        Current stock price in USD, or -1.0 if symbol not found (404)

    Raises:
        BackendAPIError: For fatal errors (5xx, timeout, rate limits)
        Exception: For unexpected errors
    """
    try:
        data = await _fetch_market_data(symbol)
        return float(data.price)
    except BackendAPIError as e:
        if e.status_code == 404:
            # Symbol not found - graceful degradation (recoverable)
            logger.warning("Symbol %s not found in market data (404) - returning sentinel", symbol)
            return -1.0
        # All other HTTP errors (429, 5xx) are fatal - let them propagate
        logger.error("Backend error for %s: %s", symbol, e)
        raise
    except Exception as e:
        # Unexpected errors (network, parsing) - also fatal
        logger.error("Unexpected error fetching %s: %s", symbol, e)
        raise

@function_tool
async def lookup_share_price(symbol: str) -> float:
    """Get the current price of a stock symbol.

    Uses real-time data from Finnhub.
    Data is cached for 60 minutes.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA', 'USMV')

    Returns:
        Current stock price in USD as a float

    Raises:
        Exception: If symbol is invalid or data unavailable
    """
    return await _lookup_share_price(symbol)


@function_tool
async def get_price_with_metadata(symbol: str) -> PriceMetadata:
    """Get stock price with metadata.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')

    Returns:
        PriceMetadata with price, cached flag, timestamp, source.
    """
    try:
        data = await _fetch_market_data(symbol)
        return PriceMetadata(
            price=data.price,
            cached=data.cached,
            timestamp=data.timestamp,
            source=data.source,
        )
    except Exception as e:
        logger.error("Failed to get price metadata for %s: %s", symbol, e)
        raise Exception(
            f"Price data unavailable for {symbol}. "
            "Skip this symbol and continue with other candidates. "
            "Do NOT retry this symbol."
        )


# All market data tools that agents can use
MARKET_TOOLS = [
    lookup_share_price,
    get_price_with_metadata,
]
