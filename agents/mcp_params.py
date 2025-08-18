#!/usr/bin/env python3

import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Environment variables
brave_api_key = os.getenv("BRAVE_API_KEY")
brave_env = {"BRAVE_API_KEY": brave_api_key} if brave_api_key else {}
polygon_api_key = os.getenv("POLYGON_API_KEY")
polygon_plan = os.getenv("POLYGON_PLAN")

# Polygon configuration
is_paid_polygon = polygon_plan == "paid"
is_realtime_polygon = polygon_plan == "realtime"

# Market MCP server configuration
if is_paid_polygon or is_realtime_polygon:
    market_mcp = {
        "command": "uvx",
        "args": ["--from", "git+https://github.com/polygon-io/mcp_polygon@v0.1.0", "mcp_polygon"],
        "env": {"POLYGON_API_KEY": polygon_api_key},
    }
else:
    market_mcp = {"command": "uv", "args": ["run", "market_server.py"]}

# The full set of MCP servers for the trader: Accounts, Push Notification and the Market
trader_mcp_server_params = [
    {"command": "python", "args": ["./mcp-servers/accounts_server.py"]},
    {"command": "python", "args": ["./mcp-servers/push_server.py"]},
    {"command": "python", "args": ["./mcp-servers/market_server.py"]},
]

# The full set of MCP servers for the researcher: Fetch, Brave Search and Memory
def researcher_mcp_server_params(name: str):
    return [
        {"command": "uvx", "args": ["mcp-server-fetch"]},
        {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": brave_env,
        },
        {
            "command": "npx",
            "args": ["-y", "mcp-memory-libsql"],
            "env": {"LIBSQL_URL": f"file:./memory/{name}.db"},
        },
    ]