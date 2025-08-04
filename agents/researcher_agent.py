"""
Researcher Agent Module

This module implements the researcher agent following the exact pattern from the source project (agents/6_mcp).
The researcher is a general-purpose financial research agent that becomes a tool for trading agents.
"""

import asyncio
import logging
from datetime import datetime
from typing import List

from agents import Agent
from agents.mcp import MCPServerStdio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def researcher_instructions():
    """
    Get the researcher instructions following the source project pattern.
    
    Returns:
        Instruction string for the researcher agent
    """
    return f"""You are a financial researcher. You are able to search the web for interesting financial news,
look for possible trading opportunities, and help with research.
Based on the request, you carry out necessary research and respond with your findings.
Take time to make multiple searches to get a comprehensive overview, and then summarize your findings.
If the web search tool raises an error due to rate limits, then use your other tool that fetches web pages instead.

Important: making use of your knowledge graph to retrieve and store information on companies, websites and market conditions:

Make use of your knowledge graph tools to store and recall entity information; use it to retrieve information that
you have worked on previously, and store new information about companies, stocks and market conditions.
Also use it to store web addresses that you find interesting so you can check them later.
Draw on your knowledge graph to build your expertise over time.

If there isn't a specific request, then just respond with investment opportunities based on searching latest news.
The current datetime is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""


def research_tool_description():
    """
    Get the research tool description following the source project pattern.
    
    Returns:
        Tool description string
    """
    return """This tool researches online for news and opportunities, \
either based on your specific request to look into a certain stock, \
or generally for notable financial news and opportunities. \
Describe what kind of research you're looking for."""


async def get_researcher(mcp_servers: List[MCPServerStdio], model_name: str = "gpt-4o-mini") -> Agent:
    """
    Create a researcher agent with the given MCP servers.
    
    This follows the exact pattern from the source project.
    
    Args:
        mcp_servers: List of MCP servers for the researcher
        model_name: Model to use for the researcher
        
    Returns:
        Configured researcher agent
    """
    researcher = Agent(
        name="Researcher",
        instructions=researcher_instructions(),
        model=model_name,
        mcp_servers=mcp_servers,
    )
    return researcher


async def get_researcher_tool(mcp_servers: List[MCPServerStdio], model_name: str = "gpt-4o-mini"):
    """
    Create a researcher tool from the researcher agent.
    
    This follows the exact pattern from the source project.
    
    Args:
        mcp_servers: List of MCP servers for the researcher
        model_name: Model to use for the researcher
        
    Returns:
        Researcher tool that can be used by other agents
    """
    researcher = await get_researcher(mcp_servers, model_name)
    return researcher.as_tool(
        tool_name="Researcher",
        tool_description=research_tool_description()
    )


# Example usage following source project pattern
async def main():
    """Example usage of the researcher agent following source project pattern."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Get MCP server parameters (following source project pattern)
    brave_env = {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")}
    
    researcher_mcp_server_params = [
        {"command": "uvx", "args": ["mcp-server-fetch"]},
        {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": brave_env,
        },
        {
            "command": "npx",
            "args": ["-y", "mcp-memory-libsql"],
            "env": {"LIBSQL_URL": "file:./memory/researcher.db"},
        },
    ]
    
    # Create MCP servers
    researcher_mcp_servers = [
        MCPServerStdio(params, client_session_timeout_seconds=30) 
        for params in researcher_mcp_server_params
    ]
    
    # Connect servers
    for server in researcher_mcp_servers:
        await server.connect()
    
    try:
        # Create researcher agent
        researcher = await get_researcher(researcher_mcp_servers, "gpt-4o-mini")
        
        # Test research request
        from agents import Runner, trace
        
        research_question = "What's the latest news on Amazon?"
        
        with trace("Researcher"):
            result = await Runner.run(researcher, research_question, max_turns=30)
        
        print("Research Result:")
        print(result.final_output)
        
    finally:
        # Clean up connections
        for server in researcher_mcp_servers:
            if hasattr(server, 'disconnect'):
                await server.disconnect()


if __name__ == "__main__":
    asyncio.run(main())