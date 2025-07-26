#!/usr/bin/env python3

import os
from dotenv import load_dotenv

load_dotenv(override=True)

# The full set of MCP servers for the trader: Accounts, Push Notification and the Market
trader_mcp_server_params = [
    {"command": "python", "args": ["accounts_server.py"]},
    {"command": "python", "args": ["push_server.py"]},
    {"command": "python", "args": ["market_server.py"]},
]

# The full set of MCP servers for the researcher: Fetch, Brave Search and Memory
def researcher_mcp_server_params(name: str):
    return [
        {"command": "uvx", "args": ["mcp-server-fetch"]},
        {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")},
        },
        {
            "command": "npx",
            "args": ["-y", "mcp-memory-libsql"],
            "env": {"LIBSQL_URL": f"file:./memory/{name}.db"},
        },
    ]