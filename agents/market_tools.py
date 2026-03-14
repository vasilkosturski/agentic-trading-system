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
from typing import Dict, List, Optional, Tuple

# Import centralized configuration
from config import BACKEND_API_MARKET

# Import unified HTTP client
from http_client import call_backend, BackendAPIError

# Import type-safe models
from models import MarketData, PriceMetadata, HistoricalPrice, MarketIndicators

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
    """
    try:
        data = await _fetch_market_data(symbol)
        return float(data.price)
    except Exception as e:
        logger.error(f"Failed to get price for {symbol}: {e}")
        raise Exception(
            f"Price data unavailable for {symbol}. "
            "Skip this symbol and continue with other candidates. "
            "Do NOT retry this symbol."
        )


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
    """Get stock price with data quality metadata.

    Provides full context about data freshness and source for informed decision-making.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')

    Returns:
        PriceMetadata model with validated data:
        - price: Current price (float)
        - dataTier: 'REAL_TIME' (Finnhub), 'MOCK' (simulated), or 'CACHED' (from cache)
        - timestamp: When data was retrieved (ISO format)
        - dataSource: 'Finnhub API' or 'Mock Data'
        - dataAgeMinutes: How old the data is
    """
    try:
        data = await _fetch_market_data(symbol)
        return PriceMetadata(
            price=data.price,
            dataTier=data.dataTier,
            timestamp=data.timestamp,
            dataSource=data.dataSource,
            dataAgeMinutes=data.dataAgeMinutes,
        )
    except Exception as e:
        logger.error(f"Failed to get price metadata for {symbol}: {e}")
        raise Exception(
            f"Price data unavailable for {symbol}. "
            "Skip this symbol and continue with other candidates. "
            "Do NOT retry this symbol."
        )


@function_tool
async def get_historical_prices(symbol: str, days: int = 30) -> List[HistoricalPrice]:
    """Get historical stock prices.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
        days: Number of days of history to retrieve (default: 30, max: 365)

    Returns:
        List of HistoricalPrice models with validated data:
        [HistoricalPrice(date="2025-01-15", price=150.25), ...]
    """
    try:
        data = await _fetch_market_data(symbol, days=days)
        return data.historicalPrices
    except Exception as e:
        logger.error(f"Failed to get historical prices for {symbol}: {e}")
        raise Exception(
            f"Price data unavailable for {symbol}. "
            "Skip this symbol and continue with other candidates. "
            "Do NOT retry this symbol."
        )


@function_tool
async def get_market_indicators(symbol: str) -> MarketIndicators:
    """Get technical market indicators for a stock.

    Includes moving averages and volatility metrics useful for analysis.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')

    Returns:
        MarketIndicators model with validated data:
        - sma5: 5-day simple moving average
        - sma20: 20-day simple moving average
        - volatility: Price volatility measure
    """
    try:
        data = await _fetch_market_data(symbol)
        return data.indicators
    except Exception as e:
        logger.error(f"Failed to get market indicators for {symbol}: {e}")
        raise Exception(
            f"Price data unavailable for {symbol}. "
            "Skip this symbol and continue with other candidates. "
            "Do NOT retry this symbol."
        )


# All market data tools that agents can use
MARKET_TOOLS = [
    lookup_share_price,
    get_price_with_metadata,
    get_historical_prices,
    get_market_indicators,
]
