#!/usr/bin/env python3

import asyncio
import aiohttp
import json
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
    """This tool provides the current price of the given stock symbol.

    Args:
        symbol: the symbol of the stock
    """
    try:
        result = await call_java_api(f"/price/{symbol}", "GET")
        return float(result)
    except Exception as e:
        raise Exception(f"Failed to get price for {symbol}: {str(e)}")

if __name__ == "__main__":
    mcp.run(transport='stdio')