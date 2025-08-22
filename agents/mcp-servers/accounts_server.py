#!/usr/bin/env python3

import asyncio
import aiohttp
import json
from mcp.server.fastmcp import FastMCP

# Configuration - Use Docker service name for container networking
JAVA_API_BASE_URL = "http://backend:8080/api/accounts"

mcp = FastMCP("accounts_server")

async def call_java_api(endpoint: str, method: str = "GET", data: dict = None):
    """Helper function to call Java Spring Boot API"""
    url = f"{JAVA_API_BASE_URL}{endpoint}"
    
    async with aiohttp.ClientSession() as session:
        if method == "GET":
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
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
async def get_balance(name: str) -> float:
    """Get the cash balance of the given account name.

    Args:
        name: The name of the account holder
    """
    try:
        result = await call_java_api("/tools/get_balance", "POST", {"name": name})
        return float(result)
    except Exception as e:
        raise Exception(f"Failed to get balance for {name}: {str(e)}")

@mcp.tool()
async def get_holdings(name: str) -> dict[str, int]:
    """Get the holdings of the given account name.

    Args:
        name: The name of the account holder
    """
    try:
        result = await call_java_api("/tools/get_holdings", "POST", {"name": name})
        return result
    except Exception as e:
        raise Exception(f"Failed to get holdings for {name}: {str(e)}")

@mcp.tool()
async def buy_shares(name: str, symbol: str, quantity: int, rationale: str) -> str:
    """Buy shares of a stock.

    Args:
        name: The name of the account holder
        symbol: The symbol of the stock
        quantity: The quantity of shares to buy
        rationale: The rationale for the purchase and fit with the account's strategy
    """
    try:
        result = await call_java_api("/tools/buy_shares", "POST", {
            "name": name,
            "symbol": symbol,
            "quantity": quantity,
            "rationale": rationale
        })
        return str(result)
    except Exception as e:
        raise Exception(f"Failed to buy shares for {name}: {str(e)}")

@mcp.tool()
async def sell_shares(name: str, symbol: str, quantity: int, rationale: str) -> str:
    """Sell shares of a stock.

    Args:
        name: The name of the account holder
        symbol: The symbol of the stock
        quantity: The quantity of shares to sell
        rationale: The rationale for the sale and fit with the account's strategy
    """
    try:
        result = await call_java_api("/tools/sell_shares", "POST", {
            "name": name,
            "symbol": symbol,
            "quantity": quantity,
            "rationale": rationale
        })
        return str(result)
    except Exception as e:
        raise Exception(f"Failed to sell shares for {name}: {str(e)}")

# change_strategy tool removed - using hardcoded strategies from constructor only
# This simplifies the design and keeps strategies consistent with trading system configuration

# MCP resources removed - using direct API calls in SimpleTrader instead
# This provides cleaner architecture: MCP tools for agents, direct API for system data

if __name__ == "__main__":
    mcp.run(transport='stdio')