from enum import StrEnum

from agents.mcp import MCPServer


class MCPName(StrEnum):
    BRAVE_SEARCH = "brave-search"
    FETCH = "fetch"


MCPPool = dict[MCPName, MCPServer]
