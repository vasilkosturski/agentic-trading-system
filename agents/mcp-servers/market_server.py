#!/usr/bin/env python3

import asyncio
import aiohttp
import json
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP

# Configuration
JAVA_API_BASE_URL = "http://backend:8080/api/market"

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
    """Get the current price of a stock symbol (backward compatibility).

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
    
    Returns:
        Current stock price as a float
    """
    try:
        result = await call_java_api(f"/price/{symbol}/value", "GET")
        return float(result)
    except Exception as e:
        raise Exception(f"Failed to get price for {symbol}: {str(e)}")

@mcp.tool()
async def get_price_with_metadata(symbol: str) -> Dict[str, Any]:
    """Get the current price of a stock symbol with data timing and quality metadata.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
    
    Returns:
        Dictionary containing price, data tier, timestamp, and data source information
    """
    try:
        result = await call_java_api(f"/price/{symbol}", "GET")
        return {
            "price": result["price"],
            "data_tier": result["dataTier"],
            "timestamp": result["timestamp"],
            "data_source": result["dataSource"],
            "data_age_minutes": result["dataAgeMinutes"]
        }
    except Exception as e:
        raise Exception(f"Failed to get price metadata for {symbol}: {str(e)}")

@mcp.tool()
async def get_historical_prices(symbol: str, days: int = 30) -> List[Dict[str, Any]]:
    """Get historical prices for a stock symbol (backward compatibility).

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
        days: Number of days of historical data (default: 30)
    
    Returns:
        List of historical price data with date and price
    """
    try:
        result = await call_java_api(f"/historical/{symbol}/prices?days={days}", "GET")
        return result
    except Exception as e:
        raise Exception(f"Failed to get historical prices for {symbol}: {str(e)}")

@mcp.tool()
async def get_historical_prices_with_metadata(symbol: str, days: int = 30) -> Dict[str, Any]:
    """Get historical prices for a stock symbol with data quality metadata.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
        days: Number of days of historical data (default: 30)
    
    Returns:
        Dictionary containing historical prices, data tier, timestamp, and warnings
    """
    try:
        result = await call_java_api(f"/historical/{symbol}?days={days}", "GET")
        return {
            "prices": result["prices"],
            "data_tier": result["dataTier"],
            "timestamp": result["timestamp"],
            "warning": result.get("warning")
        }
    except Exception as e:
        raise Exception(f"Failed to get historical prices metadata for {symbol}: {str(e)}")

@mcp.tool()
async def get_market_indicators(symbol: str) -> Dict[str, float]:
    """Get market indicators for a stock symbol including moving averages and volatility (backward compatibility).

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
    
    Returns:
        Dictionary containing sma5, sma20, and volatility indicators
    """
    try:
        result = await call_java_api(f"/indicators/{symbol}/values", "GET")
        return {
            "sma5": result["sma5"],
            "sma20": result["sma20"],
            "volatility": result["volatility"]
        }
    except Exception as e:
        raise Exception(f"Failed to get market indicators for {symbol}: {str(e)}")

@mcp.tool()
async def get_market_indicators_with_metadata(symbol: str) -> Dict[str, Any]:
    """Get market indicators for a stock symbol with data quality metadata.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
    
    Returns:
        Dictionary containing indicators, data tier, timestamp, and warnings
    """
    try:
        result = await call_java_api(f"/indicators/{symbol}", "GET")
        return {
            "indicators": {
                "sma5": result["indicators"]["sma5"],
                "sma20": result["indicators"]["sma20"],
                "volatility": result["indicators"]["volatility"]
            },
            "data_tier": result["dataTier"],
            "timestamp": result["timestamp"],
            "warning": result.get("warning")
        }
    except Exception as e:
        raise Exception(f"Failed to get market indicators metadata for {symbol}: {str(e)}")

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
    """Analyze stock trend using historical data and indicators with data quality awareness.

    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')
        days: Number of days to analyze (default: 20)
    
    Returns:
        Dictionary containing trend analysis with data quality information
    """
    try:
        # Get enhanced data with metadata
        price_data = await get_price_with_metadata(symbol)
        historical_data = await get_historical_prices_with_metadata(symbol, days)
        indicators_data = await get_market_indicators_with_metadata(symbol)
        
        current_price = price_data["price"]
        historical = historical_data["prices"]
        indicators = indicators_data["indicators"]
        
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
        
        # Collect data quality warnings
        warnings = []
        if price_data["data_tier"] == "MOCK":
            warnings.append("Current price is simulated - not suitable for real trading")
        if historical_data.get("warning"):
            warnings.append(historical_data["warning"])
        if indicators_data.get("warning"):
            warnings.append(indicators_data["warning"])
        if price_data["data_age_minutes"] > 60:
            warnings.append(f"Price data is {price_data['data_age_minutes']} minutes old")
        
        return {
            "symbol": symbol,
            "current_price": current_price,
            "price_change": round(price_change, 2),
            "price_change_percent": round(price_change_percent, 2),
            "trend": trend,
            "sma5": sma5,
            "sma20": sma20,
            "volatility": indicators["volatility"],
            "analysis_period_days": days,
            "data_quality": {
                "price_data_tier": price_data["data_tier"],
                "price_data_age_minutes": price_data["data_age_minutes"],
                "historical_data_tier": historical_data["data_tier"],
                "indicators_data_tier": indicators_data["data_tier"],
                "warnings": warnings if warnings else None
            }
        }
    except Exception as e:
        raise Exception(f"Failed to analyze trend for {symbol}: {str(e)}")

@mcp.tool()
async def get_data_freshness_report(symbols: List[str]) -> Dict[str, Any]:
    """Get a comprehensive data freshness report for multiple symbols.

    Args:
        symbols: List of stock symbols to check
    
    Returns:
        Dictionary containing data freshness information for all symbols
    """
    try:
        report = {
            "timestamp": "2024-01-01T00:00:00",  # Will be updated by actual timestamp
            "symbols_checked": len(symbols),
            "symbol_reports": {}
        }
        
        for symbol in symbols:
            try:
                price_data = await get_price_with_metadata(symbol)
                report["symbol_reports"][symbol] = {
                    "data_tier": price_data["data_tier"],
                    "data_age_minutes": price_data["data_age_minutes"],
                    "data_source": price_data["data_source"],
                    "timestamp": price_data["timestamp"],
                    "is_stale": price_data["data_age_minutes"] > 60,
                    "is_mock": price_data["data_tier"] == "MOCK"
                }
            except Exception as e:
                report["symbol_reports"][symbol] = {
                    "error": str(e)
                }
        
        # Calculate summary statistics
        valid_reports = [r for r in report["symbol_reports"].values() if "error" not in r]
        if valid_reports:
            mock_count = sum(1 for r in valid_reports if r["is_mock"])
            stale_count = sum(1 for r in valid_reports if r["is_stale"])
            
            report["summary"] = {
                "total_symbols": len(symbols),
                "valid_reports": len(valid_reports),
                "mock_data_count": mock_count,
                "stale_data_count": stale_count,
                "fresh_data_count": len(valid_reports) - stale_count - mock_count
            }
        
        return report
    except Exception as e:
        raise Exception(f"Failed to generate data freshness report: {str(e)}")

if __name__ == "__main__":
    mcp.run(transport='stdio')