#!/usr/bin/env python3

import asyncio
import logging
import os
from base_agent import BaseAgent, AgentConfig, TradingDecision
from mcp_connector import MCPManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestAgent(BaseAgent):
    """Simple test agent for foundation testing"""
    
    def get_personality_prompt(self) -> str:
        return """
You are a test trading agent designed to validate the system functionality.
Make conservative decisions and provide clear reasoning.
Focus on testing the system rather than maximizing profits.
"""

async def test_mcp_connections():
    """Test MCP server connections"""
    logger.info("Testing MCP connections...")
    
    async with MCPManager() as mcp:
        try:
            # Test market data
            price = await mcp.market.lookup_share_price("AAPL")
            logger.info(f"AAPL price: ${price}")
            
            indicators = await mcp.market.get_market_indicators("AAPL")
            logger.info(f"AAPL indicators: {indicators}")
            
            market_status = await mcp.market.get_market_status()
            logger.info(f"Market status: {market_status}")
            
            # Test notifications
            await mcp.push.send_notification("Test notification from agent foundation")
            
            logger.info("MCP connections test passed!")
            return True
            
        except Exception as e:
            logger.error(f"MCP connection test failed: {e}")
            return False

async def test_agent_creation():
    """Test agent creation and basic functionality"""
    logger.info("Testing agent creation...")
    
    # Create test agent config
    config = AgentConfig(
        name="Test Agent",
        personality="conservative",
        risk_tolerance="low",
        initial_balance=10000.0,
        openai_model="gpt-4",
        temperature=0.3
    )
    
    # Create agent
    agent = TestAgent(config)
    
    # Test MCP connection
    async with MCPManager() as mcp:
        agent.set_mcp_tools(mcp.accounts, mcp.market, mcp.push)
        
        # Initialize account
        account_id = await agent.initialize_account()
        logger.info(f"Created account: {account_id}")
        
        # Test balance retrieval
        balance = await agent.get_account_balance()
        logger.info(f"Account balance: ${balance}")
        
        # Test market data retrieval
        market_data = await agent.get_market_data("AAPL")
        logger.info(f"Market data for AAPL: {market_data}")
        
        # Test decision making (if OpenAI API key is available)
        if os.getenv('OPENAI_API_KEY'):
            logger.info("Testing OpenAI decision making...")
            try:
                decision = await agent.make_trading_decision("AAPL")
                logger.info(f"Trading decision: {decision.action} {decision.quantity} shares")
                logger.info(f"Reasoning: {decision.reasoning}")
                logger.info(f"Confidence: {decision.confidence}")
            except Exception as e:
                logger.warning(f"OpenAI decision making test failed (expected if no API key): {e}")
        else:
            logger.info("Skipping OpenAI test - no API key provided")
        
        logger.info("Agent creation test passed!")
        return True

async def main():
    """Main test function"""
    logger.info("Starting agent foundation tests...")
    
    try:
        # Test 1: MCP connections
        mcp_success = await test_mcp_connections()
        
        # Test 2: Agent creation and basic functionality
        agent_success = await test_agent_creation()
        
        # Summary
        if mcp_success and agent_success:
            logger.info("✅ All agent foundation tests passed!")
        else:
            logger.error("❌ Some tests failed")
            
    except Exception as e:
        logger.error(f"Test suite failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())