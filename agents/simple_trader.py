#!/usr/bin/env python3

import asyncio
import aiohttp
import json
import logging
from contextlib import AsyncExitStack
from datetime import datetime
from typing import List, Dict, Any

from agents import Agent, Tool, Runner, trace
from agents.mcp import MCPServerStdio
from mcp_params import trader_mcp_server_params, researcher_mcp_server_params

logger = logging.getLogger(__name__)

class SimpleTrader:
    """Simple trader using OpenAI Agents SDK with MCP - exactly like source project"""
    
    def __init__(self, name: str, strategy: str, model_name: str = "gpt-4o-mini"):
        self.name = name
        self.strategy = strategy
        self.model_name = model_name
        self.do_trade = True
        self.agent = None
    
    async def get_researcher_tool(self, researcher_mcp_servers) -> Tool:
        """Create researcher tool from MCP servers"""
        researcher_instructions = f"""You are a financial researcher. You help with research and analysis for trading decisions.
Based on the request, you carry out necessary research and respond with your findings.

Available tools:
- Web fetch tool: Can retrieve content from specific URLs
- Knowledge graph: Store and recall information about companies, websites, and market conditions

Important: making use of your knowledge graph to retrieve and store information on companies, websites and market conditions:

Make use of your knowledge graph tools to store and recall entity information; use it to retrieve information that
you have worked on previously, and store new information about companies, stocks and market conditions.
Also use it to store web addresses that you find interesting so you can check them later.
Draw on your knowledge graph to build your expertise over time.

If web search is not available, focus on analyzing known information and suggest specific URLs to fetch for research.
If there isn't a specific request, provide general investment analysis based on available information.
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
    
    def get_trade_message(self, strategy: str, account: str) -> str:
        """Get trading message - matches source project exactly"""
        return f"""Based on your investment strategy, you should now look for new opportunities.
Use the research tool to find news and opportunities consistent with your strategy.
Do not use the 'get company news' tool; use the research tool instead.
Use the tools to research stock price and other company information. You have access to end of day market data; use you get_share_price tool to get the share price as of the prior close.
Finally, make you decision, then execute trades using the tools.
Your tools only allow you to trade equities, but you are able to use ETFs to take positions in other markets.
You do not need to rebalance your portfolio; you will be asked to do so later.
Just make trades based on your strategy as needed.
Your investment strategy:
{strategy}
Here is your current account:
{account}
Here is the current datetime:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Now, carry out analysis, make your decision and execute trades. Your account name is {self.name}.
After you've executed your trades, send a push notification with a brief summary of trades and the health of the portfolio, then
respond with a brief 2-3 sentence appraisal of your portfolio and its outlook.
"""

    def get_rebalance_message(self, strategy: str, account: str) -> str:
        """Get rebalancing message - simplified without strategy changes"""
        return f"""Based on your investment strategy, you should now examine your portfolio and decide if you need to rebalance.
Use the research tool to find news and opportunities affecting your existing portfolio.
Use the tools to research stock price and other company information affecting your existing portfolio. You have access to end of day market data; use you get_share_price tool to get the share price as of the prior close.
Finally, make you decision, then execute trades using the tools as needed.
You do not need to identify new investment opportunities at this time; you will be asked to do so later.
Just rebalance your portfolio based on your strategy as needed.
Your investment strategy:
{strategy}
Here is your current account:
{account}
Here is the current datetime:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Now, carry out analysis, make your decision and execute trades. Your account name is {self.name}.
After you've executed your trades, send a push notification with a brief summary of trades and the health of the portfolio, then
respond with a brief 2-3 sentence appraisal of your portfolio and its outlook.
"""

    async def get_account_report(self) -> str:
        """Get account report via direct API call - cleaner architecture than MCP resource"""
        try:
            # Direct API call to Java backend (better than MCP resource for system data)
            url = f"http://backend:8080/api/accounts/resources/accounts/{self.name.lower()}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        account_data = await response.text()
                        
                        # Parse JSON and remove time series data to keep prompt clean (like source project)
                        account_json = json.loads(account_data)
                        account_json.pop("portfolio_value_time_series", None)
                        
                        return json.dumps(account_json)
                    else:
                        raise Exception(f"API call failed: {response.status}")
        except Exception as e:
            logger.error(f"Failed to get account report for {self.name}: {e}")
            # Fallback to basic structure if API fails
            return f'{{"name": "{self.name}", "balance": 100000, "holdings": {{}}, "error": "API unavailable"}}'

    async def get_strategy(self) -> str:
        """Get strategy - simplified to use hardcoded constructor strategy only"""
        # Return the hardcoded strategy from constructor - no persistence needed
        return self.strategy
    
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
        """Run the agent with MCP servers - matches source project exactly"""
        # Phase 5.3: Basic agent activity logging
        cycle_type = "trading" if self.do_trade else "rebalancing"
        print(f"🤖 {self.name} starting {cycle_type} cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Initialize agent account if this is the first run
        await self.ensure_agent_initialized()
        
        self.agent = await self.create_agent(trader_mcp_servers, researcher_mcp_servers)
        account = await self.get_account_report()
        strategy = await self.get_strategy()
        
        message = (
            self.get_trade_message(strategy, account)
            if self.do_trade
            else self.get_rebalance_message(strategy, account)
        )
        
        await Runner.run(self.agent, message, max_turns=30)
        
        # Phase 5.3: Log completion
        print(f"✅ {self.name} completed {cycle_type} cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
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
        """Run agent with tracing - matches source project exactly"""
        trace_name = f"{self.name}-trading" if self.do_trade else f"{self.name}-rebalancing"
        trace_id = f"trace_{self.name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with trace(trace_name, trace_id=trace_id):
            await self.run_with_mcp_servers()
    
    async def run(self):
        """Main run method - matches source project exactly"""
        try:
            logger.info(f"Starting {self.name} agent...")
            await self.run_with_trace()
            logger.info(f"{self.name} agent completed successfully")
        except Exception as e:
            logger.error(f"Error running {self.name} agent: {e}")
        # Toggle between trading and rebalancing - matches source project exactly
        self.do_trade = not self.do_trade
    
    async def ensure_agent_initialized(self):
        """Ensure agent account is initialized before trading operations"""
        try:
            # Call the Java backend to initialize the agent
            url = "http://backend:8080/api/accounts/tools/initialize_agent"
            data = {
                "name": self.name,
                "initialBalance": 100000.0
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers={"Content-Type": "application/json"}) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("success"):
                            logger.info(f"✅ {self.name} agent initialized successfully")
                        else:
                            # Agent might already be initialized, which is fine
                            logger.debug(f"Agent {self.name} initialization response: {result.get('error', 'Unknown')}")
                    else:
                        logger.warning(f"Failed to initialize {self.name} agent: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Error initializing {self.name} agent: {e}")
            # Don't fail the entire agent run if initialization fails