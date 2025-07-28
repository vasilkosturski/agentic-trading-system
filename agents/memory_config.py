#!/usr/bin/env python3

import os
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class MemoryServerConfig:
    """Configuration for LibSQL Memory MCP server"""
    agent_name: str
    database_path: str
    
    def get_mcp_params(self) -> Dict[str, Any]:
        """Get MCP server parameters for mcp-memory-libsql"""
        return {
            "command": "npx",
            "args": ["-y", "mcp-memory-libsql"],
            "env": {"LIBSQL_URL": f"file:{self.database_path}"}
        }

class MemoryManager:
    """Manager for LibSQL Memory configurations"""
    
    def __init__(self, base_memory_dir: str = "./agents/memory"):
        self.base_memory_dir = base_memory_dir
        self._ensure_memory_directory()
    
    def _ensure_memory_directory(self):
        """Ensure memory directory exists"""
        os.makedirs(self.base_memory_dir, exist_ok=True)
    
    def get_memory_config(self, agent_name: str) -> MemoryServerConfig:
        """Get memory configuration for a specific agent"""
        database_path = os.path.join(self.base_memory_dir, f"{agent_name.lower()}.db")
        return MemoryServerConfig(
            agent_name=agent_name,
            database_path=database_path
        )
    
    def get_researcher_mcp_params(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get MCP server parameters for researcher with memory (similar to agents/6_mcp)"""
        memory_config = self.get_memory_config(agent_name)
        
        return [
            # Fetch server for web content
            {"command": "uvx", "args": ["mcp-server-fetch"]},
            
            # Brave search server (if API key available)
            {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                "env": {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY", "")}
            },
            
            # LibSQL Memory server
            memory_config.get_mcp_params()
        ]
    
    def get_trader_mcp_params(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get MCP server parameters for trader agents"""
        return [
            # Account management server
            {"command": "python", "args": ["mcp-servers/accounts_server.py"]},
            
            # Push notification server
            {"command": "python", "args": ["mcp-servers/push_server.py"]},
            
            # Market data server
            {"command": "python", "args": ["mcp-servers/market_server.py"]}
        ]

# Global memory manager instance
memory_manager = MemoryManager()

# Memory instructions for agents (based on agents/6_mcp templates)
MEMORY_INSTRUCTIONS = """
Important: Making use of your knowledge graph to retrieve and store information on companies, websites and market conditions:

Make use of your knowledge graph tools to store and recall entity information; use it to retrieve information that
you have worked on previously, and store new information about companies, stocks and market conditions.
Also use it to store web addresses that you find interesting so you can check them later.
Draw on your knowledge graph to build your expertise over time.

You can use your entity tools as a persistent memory to store and recall information; you share
this memory with other traders and can benefit from the group's knowledge.
"""

RESEARCHER_MEMORY_INSTRUCTIONS = """
You are a financial researcher with access to persistent memory through knowledge graph tools.

Based on the request, you carry out necessary research and respond with your findings.
Take time to make multiple searches to get a comprehensive overview, and then summarize your findings.

{memory_instructions}

If there isn't a specific request, then just respond with investment opportunities based on searching latest news.
""".format(memory_instructions=MEMORY_INSTRUCTIONS)

TRADER_MEMORY_INSTRUCTIONS = """
You actively manage your portfolio according to your strategy.
You have access to tools including a researcher to research online for news and opportunities, based on your request.

{memory_instructions}

Use these tools to carry out research, make decisions, and execute trades.
Your goal is to maximize your profits according to your strategy.
""".format(memory_instructions=MEMORY_INSTRUCTIONS)