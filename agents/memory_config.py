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
        database_path = os.path.abspath(os.path.join(self.base_memory_dir, f"{agent_name.lower()}.db"))
        return MemoryServerConfig(
            agent_name=agent_name,
            database_path=database_path
        )
    
    def get_researcher_mcp_params(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get MCP server parameters for researcher with memory - Brave Search + LibSQL Memory"""
        memory_config = self.get_memory_config(agent_name)
        
        servers = []
        
        # Brave search server (primary research tool)
        brave_api_key = os.getenv("BRAVE_API_KEY", "")
        if brave_api_key:
            servers.append({
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                "env": {"BRAVE_API_KEY": brave_api_key}
            })
        
        # Fetch server (fallback for web content)
        servers.append({
            "command": "uvx",
            "args": ["mcp-server-fetch"]
        })
        
        # LibSQL Memory server (always included)
        servers.append(memory_config.get_mcp_params())
        
        return servers
    
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
If the web search tool raises an error due to rate limits, then use your other tool that fetches web pages instead.

{memory_instructions}

If there isn't a specific request, then just respond with investment opportunities based on searching latest news.
""".format(memory_instructions=MEMORY_INSTRUCTIONS)

# Research tool description following agents/6_mcp pattern
RESEARCH_TOOL_DESCRIPTION = """This tool researches online for news and opportunities,
either based on your specific request to look into a certain stock,
or generally for notable financial news and opportunities.
Describe what kind of research you're looking for."""

TRADER_MEMORY_INSTRUCTIONS = """
You actively manage your portfolio according to your strategy.
You have access to tools including a researcher to research online for news and opportunities, based on your request.
You also have tools to access financial data for stocks and tools to buy and sell stocks using your account.

{memory_instructions}

Use these tools to carry out research, make decisions, and execute trades.
After you've completed trading, send a push notification with a brief summary of activity, then reply with a 2-3 sentence appraisal.
Your goal is to maximize your profits according to your strategy.

IMPORTANT: Use the research tool to find news and opportunities consistent with your strategy.
Do not use direct market data tools for company news; use the research tool instead.
The research tool provides comprehensive financial news analysis and market sentiment.
""".format(memory_instructions=MEMORY_INSTRUCTIONS)

# Researcher tool factory function following agents/6_mcp pattern
async def get_researcher_tool(agent_name: str, model_name: str = "gpt-4o-mini"):
    """
    Create researcher tool for trading agents
    Following the exact pattern from agents/6_mcp/traders.py:62-64
    """
    from researcher_agent import get_researcher_tool as create_researcher_tool
    from mcp_connector import MCPManager
    
    try:
        # Get researcher MCP server parameters
        researcher_mcp_params = memory_manager.get_researcher_mcp_params(agent_name)
        
        # Create MCP manager for researcher (this would need to be implemented)
        # For now, we'll create a placeholder that returns the researcher tool
        
        # Import and create researcher tool
        researcher_tool = await create_researcher_tool(researcher_mcp_params, model_name)
        
        return researcher_tool
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create researcher tool for {agent_name}: {e}")
        
        # Return a fallback tool that indicates research is unavailable
        return {
            "name": "Researcher",
            "description": "Research tool unavailable due to configuration error",
            "function": lambda request: f"Research unavailable: {str(e)}",
            "parameters": {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "string",
                        "description": "The research request or query"
                    }
                },
                "required": ["request"]
            }
        }