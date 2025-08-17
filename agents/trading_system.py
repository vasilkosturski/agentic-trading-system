#!/usr/bin/env python3

import asyncio
import logging
from contextlib import AsyncExitStack
from datetime import datetime
from typing import List, Dict, Any

from agents import Agent, Tool, Runner, trace
from agents.mcp import MCPServerStdio
from mcp_params import trader_mcp_server_params, researcher_mcp_server_params

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleTrader:
    """Simple trader using OpenAI Agents SDK with MCP - exactly like source project"""
    
    def __init__(self, name: str, strategy: str, model_name: str = "gpt-4o-mini"):
        self.name = name
        self.strategy = strategy
        self.model_name = model_name
        self.do_trade = True
    
    async def get_researcher_tool(self, researcher_mcp_servers) -> Tool:
        """Create researcher tool from MCP servers"""
        researcher_instructions = f"""You are a financial researcher. You are able to search the web for interesting financial news,
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
        
        researcher = Agent(
            name="Researcher",
            instructions=researcher_instructions,
            model=self.model_name,
            mcp_servers=researcher_mcp_servers,
        )
        
        return researcher.as_tool(
            tool_name="Researcher",
            tool_description="This tool researches online for news and opportunities, either based on your specific request to look into a certain stock, or generally for notable financial news and opportunities. Describe what kind of research you're looking for."
        )
    
    def get_trader_instructions(self) -> str:
        """Get trader instructions"""
        return f"""
You are {self.name}, a trader on the stock market. Your account is under your name, {self.name}.
You actively manage your portfolio according to your strategy.
You have access to tools including a researcher to research online for news and opportunities, based on your request.
You also have tools to access to financial data for stocks. You have access to end of day market data; use you lookup_share_price tool to get the share price as of the prior close.
And you have tools to buy and sell stocks using your account name {self.name}.
You can use your entity tools as a persistent memory to store and recall information; you share
this memory with other traders and can benefit from the group's knowledge.
Use these tools to carry out research, make decisions, and execute trades.
After you've completed trading, send a push notification with a brief summary of activity, then reply with a 2-3 sentence appraisal.
Your goal is to maximize your profits according to your strategy.

Your investment strategy:
{self.strategy}
"""
    
    def get_trade_message(self) -> str:
        """Get trading message"""
        return f"""Based on your investment strategy, you should now look for new opportunities.
Use the research tool to find news and opportunities consistent with your strategy.
Do not use the 'get company news' tool; use the research tool instead.
Use the tools to research stock price and other company information. You have access to end of day market data; use you lookup_share_price tool to get the share price as of the prior close.
Finally, make you decision, then execute trades using the tools.
Your tools only allow you to trade equities, but you are able to use ETFs to take positions in other markets.
You do not need to rebalance your portfolio; you will be asked to do so later.
Just make trades based on your strategy as needed.
Your investment strategy:
{self.strategy}
Here is the current datetime:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Now, carry out analysis, make your decision and execute trades. Your account name is {self.name}.
After you've executed your trades, send a push notification with a brief summary of trades and the health of the portfolio, then
respond with a brief 2-3 sentence appraisal of your portfolio and its outlook.
"""
    
    async def create_agent(self, trader_mcp_servers, researcher_mcp_servers) -> Agent:
        """Create the agent with MCP servers"""
        researcher_tool = await self.get_researcher_tool(researcher_mcp_servers)
        
        agent = Agent(
            name=self.name,
            instructions=self.get_trader_instructions(),
            model=self.model_name,
            tools=[researcher_tool],
            mcp_servers=trader_mcp_servers,
        )
        
        return agent
    
    async def run_agent(self, trader_mcp_servers, researcher_mcp_servers):
        """Run the agent with MCP servers"""
        agent = await self.create_agent(trader_mcp_servers, researcher_mcp_servers)
        message = self.get_trade_message()
        
        await Runner.run(agent, message, max_turns=30)
    
    async def run_with_mcp_servers(self):
        """Run agent with MCP server context managers"""
        async with AsyncExitStack() as stack:
            trader_mcp_servers = [
                await stack.enter_async_context(
                    MCPServerStdio(params, client_session_timeout_seconds=120)
                )
                for params in trader_mcp_server_params
            ]
            
            async with AsyncExitStack() as stack2:
                researcher_mcp_servers = [
                    await stack2.enter_async_context(
                        MCPServerStdio(params, client_session_timeout_seconds=120)
                    )
                    for params in researcher_mcp_server_params(self.name.lower())
                ]
                
                await self.run_agent(trader_mcp_servers, researcher_mcp_servers)
    
    async def run_with_trace(self):
        """Run agent with tracing"""
        trace_name = f"{self.name}-trading"
        trace_id = f"trace_{self.name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with trace(trace_name, trace_id=trace_id):
            await self.run_with_mcp_servers()
    
    async def run(self):
        """Main run method"""
        try:
            logger.info(f"Starting {self.name} agent...")
            await self.run_with_trace()
            logger.info(f"{self.name} agent completed successfully")
        except Exception as e:
            logger.error(f"Error running {self.name} agent: {e}")
            raise

class TradingSystem:
    """Main trading system that orchestrates all four autonomous agents"""
    
    def __init__(self):
        # Create the four legendary traders with their strategies
        self.agents = [
            SimpleTrader("Warren", """
You are Warren, and you are named in homage to your role model, Warren Buffett.
You are a value-oriented investor who prioritizes long-term wealth creation.
You identify high-quality companies trading below their intrinsic value.
You invest patiently and hold positions through market fluctuations, 
relying on meticulous fundamental analysis, steady cash flows, strong management teams, 
and competitive advantages. You rarely react to short-term market movements, 
trusting your deep research and value-driven strategy.
"""),
            SimpleTrader("George", """
You are George, and you are named in homage to your role model, George Soros.
You are a contrarian macro investor who focuses on large-scale economic and political trends.
You use reflexivity theory to identify market inefficiencies and bubbles.
You're willing to take large, concentrated positions when you have high conviction,
and you're not afraid to go against conventional wisdom. You focus on currencies,
commodities, and broad market movements, looking for paradigm shifts and market dislocations.
"""),
            SimpleTrader("Ray", """
You are Ray, and you are named in homage to your role model, Ray Dalio.
You are a systematic investor who focuses on risk parity and diversification.
You believe in building all-weather portfolios that can perform across different economic environments.
You use systematic approaches, focus on uncorrelated returns, and emphasize risk management.
You look for balance across asset classes and economic regimes, preferring steady,
risk-adjusted returns over high-risk, high-reward strategies.
"""),
            SimpleTrader("Cathie", """
You are Cathie, and you are named in homage to your role model, Cathie Wood.
You are a growth investor focused on disruptive innovation and exponential technologies.
You invest in companies that are transforming industries through artificial intelligence,
robotics, autonomous vehicles, blockchain, and other breakthrough technologies.
You have a long-term investment horizon and are willing to accept high volatility
in exchange for the potential of exponential returns from revolutionary companies.
""")
        ]
    
    async def run_all_agents(self):
        """Run all four agents concurrently"""
        logger.info("🚀 Starting all four autonomous trading agents...")
        
        # Print agent summary
        self.print_agent_summary()
        
        # Run all agents concurrently
        tasks = [agent.run() for agent in self.agents]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("✅ All agents completed their trading cycle")
    
    def print_agent_summary(self):
        """Print a summary of all agents"""
        print("\n" + "="*80)
        print("🏛️  AGENTIC TRADING SYSTEM - AGENT ROSTER")
        print("="*80)
        
        agent_info = [
            {
                "name": "Warren",
                "style": "Value Investor",
                "inspiration": "Warren Buffett",
                "approach": "Long-term value, conservative, fundamentals-focused",
                "risk": "Conservative"
            },
            {
                "name": "George", 
                "style": "Contrarian Macro",
                "inspiration": "George Soros",
                "approach": "Contrarian, macro-focused, reflexivity theory",
                "risk": "Aggressive"
            },
            {
                "name": "Ray",
                "style": "Risk Parity",
                "inspiration": "Ray Dalio", 
                "approach": "Diversified, systematic, risk-adjusted returns",
                "risk": "Moderate"
            },
            {
                "name": "Cathie",
                "style": "Growth Innovation",
                "inspiration": "Cathie Wood",
                "approach": "Disruptive innovation, exponential growth",
                "risk": "Aggressive"
            }
        ]
        
        for agent in agent_info:
            print(f"👤 {agent['name']} ({agent['style']})")
            print(f"   📚 Inspired by: {agent['inspiration']}")
            print(f"   🎯 Approach: {agent['approach']}")
            print(f"   ⚡ Risk Level: {agent['risk']}")
            print()
        
        print("="*80 + "\n")

async def main():
    """Main function"""
    logger.info("🚀 Starting Agentic Trading System...")
    
    try:
        system = TradingSystem()
        await system.run_all_agents()
        logger.info("✅ Trading system completed successfully")
    except Exception as e:
        logger.error(f"❌ Trading system failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())