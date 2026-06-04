"""MCP-related type definitions."""

from enum import Enum


class MCPServerName(str, Enum):
    """Valid MCP server names.

    Using an enum prevents typos and provides IDE autocomplete.
    """

    BRAVE_SEARCH = "brave-search"
    FETCH = "fetch"
    MEMORY = "memory"
