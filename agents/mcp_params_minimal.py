#!/usr/bin/env python3

import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Environment variables
brave_api_key = os.getenv("BRAVE_API_KEY")
brave_env = {"BRAVE_API_KEY": brave_api_key} if brave_api_key else {}

# Minimal MCP server configuration for testing - only one server at a time
trader_mcp_server_params = [
    {"command": "uv", "args": ["run", "./mcp-servers/push_server.py"]},  # Simplest server - no HTTP calls
]

# Minimal researcher MCP servers - test one at a time
def researcher_mcp_server_params(name: str):
    return [
        # Test only Brave Search first (most likely to work)
        {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": brave_env,
        },
    ]