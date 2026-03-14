#!/usr/bin/env python3
"""
MCP Types - Type-safe MCP server management

Defines available MCP servers and type hints for MCP pools.
Each agent declares which MCPs it needs via REQUIRED_MCPS.
"""

from enum import StrEnum
from typing import Dict
from agents.mcp import MCPServer


class MCPName(StrEnum):
    """Available MCP servers in the system"""
    BRAVE_SEARCH = "brave-search"
    FETCH = "fetch"


# Type alias for MCP pool
MCPPool = Dict[MCPName, MCPServer]
