#!/usr/bin/env python3
"""
Direct HTTP market data tools - replaces market_server.py MCP proxy
Uses OpenAI Agents SDK @function_tool decorator for automatic schema generation
"""

import logging
from agents import function_tool
from typing import List, Any

# Import centralized configuration
from config import BACKEND_API_MARKET

# Import unified HTTP client
from http_client import call_backend, BackendAPIError

# Import type-safe models
from models import PriceMetadata, HistoricalPrice, MarketIndicators

logger = logging.getLogger(__name__)

# Use centralized configuration
BACKEND_URL = BACKEND_API_MARKET

async def _call_backend_api(endpoint: str) -> Any:
    """Helper to call Java backend API"""
    url = f"{BACKEND_URL}{endpoint}"

    try:
        response = await call_backend("GET", url)
        result = response.json()

        if result.get("success"):
            return result.get("data")
        else:
            # Shouldn't happen (backend returns 4xx/5xx on error)
            error_msg = result.get("error", "Unknown error")
            raise Exception(f"API call failed: {error_msg}")

    except BackendAPIError as e:
        # Already logged by http_client
        raise Exception(str(e)) from e

@function_tool
async def lookup_share_price(symbol: str) -> float:
    """Get the current price of a stock symbol.

    Uses end-of-day data from Polygon.io (previous trading day close).
    Data is cached for 60 minutes.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA', 'USMV')

    Returns:
        Current stock price in USD as a float

    Raises:
        Exception: If symbol is invalid or data unavailable
    """
    try:
        result = await _call_backend_api(f"/price/{symbol}/value")
        return float(result)
    except Exception as e:
        logger.error(f"Failed to get price for {symbol}: {e}")
        raise Exception(f"Failed to get price for {symbol}: {str(e)}")

@function_tool
async def get_price_with_metadata(symbol: str) -> PriceMetadata:
    """Get stock price with data quality metadata.

    Provides full context about data freshness and source for informed decision-making.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')

    Returns:
        PriceMetadata model with validated data:
        - price: Current price (float)
        - dataTier: 'REAL' (Polygon.io), 'MOCK' (simulated), or 'CACHED' (from cache)
        - timestamp: When data was retrieved (ISO format)
        - dataSource: 'Polygon.io API' or 'Mock Data'
        - dataAgeMinutes: How old the data is
    """
    try:
        result = await _call_backend_api(f"/price/{symbol}")
        # Validate API response with Pydantic
        return PriceMetadata(**result)
    except Exception as e:
        logger.error(f"Failed to get price metadata for {symbol}: {e}")
        raise Exception(f"Failed to get price metadata for {symbol}: {str(e)}")

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
        result = await _call_backend_api(f"/historical/{symbol}/prices?days={days}")
        # Validate API response with Pydantic
        return [HistoricalPrice(**item) for item in result]
    except Exception as e:
        logger.error(f"Failed to get historical prices for {symbol}: {e}")
        raise Exception(f"Failed to get historical prices for {symbol}: {str(e)}")

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
        result = await _call_backend_api(f"/indicators/{symbol}/values")
        # Validate API response with Pydantic
        return MarketIndicators(**result)
    except Exception as e:
        logger.error(f"Failed to get market indicators for {symbol}: {e}")
        raise Exception(f"Failed to get market indicators for {symbol}: {str(e)}")

# All market data tools that agents can use
MARKET_TOOLS = [
    lookup_share_price,
    get_price_with_metadata,
    get_historical_prices,
    get_market_indicators,
]
