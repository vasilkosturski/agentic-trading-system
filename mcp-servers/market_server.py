#!/usr/bin/env python3

import asyncio
import aiohttp
import json
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP

# Configuration
JAVA_API_BASE_URL = "http://localhost:8080/api/market"

mcp = FastMCP("market_server")

async def call_java_api(endpoint: str, method: str = "GET", data: dict = None):
    """Helper function to call Java Spring Boot API"""
    url = f"{JAVA_API_BASE_URL}{endpoint}"
    
    async with aiohttp.ClientSession() as session:
        if method == "GET":
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        return result.get("data")
                    else:
                        raise Exception(result.get("error", "Unknown error"))
                else:
                    raise Exception(f"API call failed: {response.status}")
        elif method == "POST":
            headers = {"Content-Type": "application/json"}
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        return result.get("data")
                    else:
                        raise Exception(result.get("error", "Unknown error"))
                else:
                    raise Exception(f"API call failed: {response.status}")

@mcp.tool()
async def lookup_share_price(symbol: str) -> float:
    """Get the current price of a stock symbol.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
    
    Returns:
        Current stock price as a float
    """
    try:
        result = await call_java_api(f"/price/{symbol}", "GET")
        return float(result)
    except Exception as e:
        raise Exception(f"Failed to get price for {symbol}: {str(e)}")

@mcp.tool()
async def get_historical_prices(symbol: str, days: int = 30) -> List[Dict[str, Any]]:
    """Get historical prices for a stock symbol.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
        days: Number of days of historical data (default: 30)
    
    Returns:
        List of historical price data with date and price
    """
    try:
        result = await call_java_api(f"/historical/{symbol}?days={days}", "GET")
        return result
    except Exception as e:
        raise Exception(f"Failed to get historical prices for {symbol}: {str(e)}")

@mcp.tool()
async def get_market_indicators(symbol: str) -> Dict[str, float]:
    """Get market indicators for a stock symbol including moving averages and volatility.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
    
    Returns:
        Dictionary containing sma5, sma20, and volatility indicators
    """
    try:
        result = await call_java_api(f"/indicators/{symbol}", "GET")
        return {
            "sma5": result["sma5"],
            "sma20": result["sma20"],
            "volatility": result["volatility"]
        }
    except Exception as e:
        raise Exception(f"Failed to get market indicators for {symbol}: {str(e)}")

@mcp.tool()
async def get_market_status() -> Dict[str, str]:
    """Get current market status information.
    
    Returns:
        Dictionary containing market status, next event, and current time
    """
    try:
        result = await call_java_api("/status", "GET")
        return {
            "status": result["status"],
            "next_event": result["nextEvent"],
            "current_time": result["currentTime"]
        }
    except Exception as e:
        raise Exception(f"Failed to get market status: {str(e)}")

@mcp.tool()
async def is_market_open() -> bool:
    """Check if the market is currently open.
    
    Returns:
        True if market is open, False otherwise
    """
    try:
        result = await call_java_api("/is-open", "GET")
        return bool(result)
    except Exception as e:
        raise Exception(f"Failed to check market status: {str(e)}")

@mcp.tool()
async def clear_price_cache() -> str:
    """Clear the market data price cache to force fresh data retrieval.
    
    Returns:
        Success message
    """
    try:
        result = await call_java_api("/cache/clear", "POST")
        return str(result)
    except Exception as e:
        raise Exception(f"Failed to clear cache: {str(e)}")

@mcp.tool()
async def analyze_stock_trend(symbol: str, days: int = 20) -> Dict[str, Any]:
    """Analyze stock trend using historical data and indicators.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
        days: Number of days to analyze (default: 20)
    
    Returns:
        Dictionary containing trend analysis
    """
    try:
        # Get current price, historical data, and indicators
        current_price = await lookup_share_price(symbol)
        historical = await get_historical_prices(symbol, days)
        indicators = await get_market_indicators(symbol)
        
        # Calculate trend
        if len(historical) >= 2:
            start_price = historical[0]["price"]
            end_price = historical[-1]["price"]
            price_change = end_price - start_price
            price_change_percent = (price_change / start_price) * 100
        else:
            price_change = 0
            price_change_percent = 0
        
        # Determine trend direction
        sma5 = indicators["sma5"]
        sma20 = indicators["sma20"]
        
        if sma5 > sma20:
            trend = "BULLISH"
        elif sma5 < sma20:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"
        
        return {
            "symbol": symbol,
            "current_price": current_price,
            "price_change": round(price_change, 2),
            "price_change_percent": round(price_change_percent, 2),
            "trend": trend,
            "sma5": sma5,
            "sma20": sma20,
            "volatility": indicators["volatility"],
            "analysis_period_days": days
        }
    except Exception as e:
        raise Exception(f"Failed to analyze trend for {symbol}: {str(e)}")

if __name__ == "__main__":
    mcp.run(transport='stdio')