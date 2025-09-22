#!/usr/bin/env python3

import asyncio
import logging
from contextlib import AsyncExitStack
from datetime import datetime

from agents import Agent, Runner, trace
from agents.mcp import MCPServerStdio
from mcp_params_minimal import trader_mcp_server_params, researcher_mcp_server_params

logger = logging.getLogger(__name__)

class SimpleTraderTest:
    """Simplified trader for testing MCP server initialization issues"""
    
    def __init__(self, name: str = "TestAgent"):
        self.name = name
        self.model_name = "gpt-4o-mini"
    
    async def create_agent(self, trader_mcp_servers, researcher_mcp_servers) -> Agent:
        """Create minimal agent for testing"""
        agent = Agent(
            name=self.name,
            instructions=f"You are {self.name}, a test trading agent. Just respond with 'MCP servers initialized successfully!'",
            model=self.model_name,
            mcp_servers=trader_mcp_servers + researcher_mcp_servers,
        )
        return agent
    
    async def run_agent(self, trader_mcp_servers, researcher_mcp_servers):
        """Run minimal agent test"""
        print(f"🧪 {self.name} starting MCP initialization test at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.agent = await self.create_agent(trader_mcp_servers, researcher_mcp_servers)
        
        await Runner.run(self.agent, "Test MCP server initialization", max_turns=1)
        
        print(f"✅ {self.name} MCP test completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    async def run_with_mcp_servers(self):
        """Run with minimal MCP servers"""
        async with AsyncExitStack() as stack:
            print(f"🔧 Initializing trader MCP servers: {len(trader_mcp_server_params)} servers")
            trader_mcp_servers = [
                await stack.enter_async_context(
                    MCPServerStdio(params, client_session_timeout_seconds=120)
                )
                for params in trader_mcp_server_params
            ]
            
            async with AsyncExitStack() as stack2:
                print(f"🔧 Initializing researcher MCP servers: {len(researcher_mcp_server_params(self.name.lower()))} servers")
                researcher_mcp_servers = [
                    await stack2.enter_async_context(
                        MCPServerStdio(params, client_session_timeout_seconds=120)
                    )
                    for params in researcher_mcp_server_params(self.name.lower())
                ]
                
                await self.run_agent(trader_mcp_servers, researcher_mcp_servers)
    
    async def run(self):
        """Main test method"""
        try:
            logger.info(f"Starting {self.name} MCP test...")
            await self.run_with_mcp_servers()
            logger.info(f"{self.name} MCP test completed successfully")
        except Exception as e:
            logger.error(f"Error in {self.name} MCP test: {e}")
            raise

async def main():
    """Test minimal MCP configuration"""
    logger.info("🧪 Starting minimal MCP server test...")
    
    try:
        test_agent = SimpleTraderTest("MCPTest")
        await test_agent.run()
        logger.info("✅ Minimal MCP test completed successfully")
    except Exception as e:
        logger.error(f"❌ Minimal MCP test failed: {e}")
        raise

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🧪 Running minimal MCP server test")
    asyncio.run(main())