#!/usr/bin/env python3
"""
MCP Parameters - Refactored to only include EXTERNAL MCPs

Internal MCPs removed:
- accounts_server.py → Replaced by trading_tools.py (direct HTTP)
- market_server.py → Replaced by market_tools.py (direct HTTP)

External MCPs kept:
- Brave Search → Third-party web search service
- Memory (libsql) → Third-party memory storage
- Fetch → Standard web content retrieval

Push notifications server kept as separate process (could also be refactored but lower priority)
"""

import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Environment variables
brave_api_key = os.getenv("BRAVE_API_KEY")
brave_env = {"BRAVE_API_KEY": brave_api_key} if brave_api_key else {}

# researcher_mcp_server_params - External MCPs for web research
# These are legitimate MCPs - we don't control these services
def researcher_mcp_server_params(name: str):
    """
    MCP servers for researcher tool - EXTERNAL services only

    - mcp-server-fetch: Standard web content retrieval
    - Brave Search: Third-party web search API
    - Memory (libsql): Third-party memory/context storage

    Args:
        name: Agent name for unique memory database

    Returns:
        List of MCP server parameter dicts
    """
    return [
        # Fetch - Standard web content retrieval
        {"command": "uvx", "args": ["mcp-server-fetch"]},

        # Brave Search - Third-party web search (legitimate MCP use case)
        {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": brave_env,
        },

        # Memory - Third-party context storage (legitimate MCP use case)
        {
            "command": "npx",
            "args": ["-y", "mcp-memory-libsql"],
            "env": {"LIBSQL_URL": f"file:./memory/{name}.db"},
        },
    ]