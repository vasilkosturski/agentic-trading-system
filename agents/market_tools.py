#!/usr/bin/env python3
"""
Direct HTTP market data tools - replaces market_server.py MCP proxy
Uses OpenAI Agents SDK @function_tool decorator for automatic schema generation
"""

import aiohttp
import logging
from agents import function_tool
from typing import Dict, List, Any

# Import centralized configuration
from config import BACKEND_API_MARKET

logger = logging.getLogger(__name__)

# Use centralized configuration
BACKEND_URL = BACKEND_API_MARKET

async def _call_backend_api(endpoint: str) -> any:
    """Helper to call Java backend API"""
    url = f"{BACKEND_URL}{endpoint}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            result = await response.json()
            if response.status == 200 and result.get("success"):
                return result.get("data")
            else:
                error_msg = result.get("error", "Unknown error")
                raise Exception(f"API call failed: {error_msg}")

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
async def get_price_with_metadata(symbol: str) -> Dict[str, Any]:
    """Get stock price with data quality metadata.

    Provides full context about data freshness and source for informed decision-making.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')

    Returns:
        Dictionary with:
        - price: Current price (float)
        - data_tier: 'REAL' (Polygon.io), 'MOCK' (simulated), or 'CACHED' (from cache)
        - timestamp: When data was retrieved (ISO format)
        - data_source: 'Polygon.io API' or 'Mock Data'
        - data_age_minutes: How old the data is
    """
    try:
        result = await _call_backend_api(f"/price/{symbol}")
        return {
            "price": result["price"],
            "data_tier": result["dataTier"],
            "timestamp": result["timestamp"],
            "data_source": result["dataSource"],
            "data_age_minutes": result["dataAgeMinutes"]
        }
    except Exception as e:
        logger.error(f"Failed to get price metadata for {symbol}: {e}")
        raise Exception(f"Failed to get price metadata for {symbol}: {str(e)}")

@function_tool
async def get_historical_prices(symbol: str, days: int = 30) -> List[Dict[str, Any]]:
    """Get historical stock prices.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
        days: Number of days of history to retrieve (default: 30, max: 365)

    Returns:
        List of dictionaries with date and price:
        [{"date": "2025-01-15", "price": 150.25}, ...]
    """
    try:
        result = await _call_backend_api(f"/historical/{symbol}/prices?days={days}")
        return result
    except Exception as e:
        logger.error(f"Failed to get historical prices for {symbol}: {e}")
        raise Exception(f"Failed to get historical prices for {symbol}: {str(e)}")

@function_tool
async def get_market_indicators(symbol: str) -> Dict[str, float]:
    """Get technical market indicators for a stock.

    Includes moving averages and volatility metrics useful for analysis.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')

    Returns:
        Dictionary with:
        - sma5: 5-day simple moving average
        - sma20: 20-day simple moving average
        - volatility: Price volatility measure
    """
    try:
        result = await _call_backend_api(f"/indicators/{symbol}/values")
        return {
            "sma5": result["sma5"],
            "sma20": result["sma20"],
            "volatility": result["volatility"]
        }
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
