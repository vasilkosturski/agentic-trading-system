#!/usr/bin/env python3
"""
MCP Parameters - Refactored to only include EXTERNAL MCPs

Internal MCPs removed:
- accounts_server.py → Replaced by trading_tools.py (direct HTTP)
- market_server.py → Replaced by market_tools.py (direct HTTP)

External MCPs kept:
- Brave Search → Third-party web search service
- Fetch → Standard web content retrieval

Memory is now stored in PostgreSQL directly via trading_tools.py (no separate MCP needed).
"""

import os
from typing import Dict
from dotenv import load_dotenv
from mcp_helpers.types import MCPName

load_dotenv(override=True)

# Environment variables
brave_api_key = os.getenv("BRAVE_API_KEY")
brave_env = {"BRAVE_API_KEY": brave_api_key} if brave_api_key else {}

# MCP server parameters - External MCPs for web research
# These are legitimate MCPs - we don't control these services
def get_mcp_server_params() -> Dict[MCPName, dict]:
    """
    Get MCP server parameters as a dict keyed by MCPName.

    Returns dict with configuration for each available MCP server:
    - FETCH: Standard web content retrieval
    - BRAVE_SEARCH: Third-party web search API

    NOTE: Memory is now stored in PostgreSQL directly via trading_tools.py
    No separate MCP needed - use PostgreSQL fields (full_reasoning, research_sources, agent_context)

    Returns:
        Dict[MCPName, dict] - MCP server configuration by name
    """
    return {
        MCPName.FETCH: {
            "command": "mcp-server-fetch",
            "args": []
        },
        MCPName.BRAVE_SEARCH: {
            "command": "mcp-server-brave-search",
            "args": [],
            "env": brave_env,
        },
    }


# Backwards compatibility - deprecated
def researcher_mcp_server_params(name: str):
    """
    DEPRECATED: Use get_mcp_server_params() instead.

    Returns list of MCP server parameter dicts (old format).
    """
    params_dict = get_mcp_server_params()
    return list(params_dict.values())