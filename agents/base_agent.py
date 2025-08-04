#!/usr/bin/env python3

from contextlib import AsyncExitStack
from agents import Agent, Tool, Runner, OpenAIChatCompletionsModel, trace
from agents.mcp import MCPServerStdio
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

load_dotenv(override=True)

# Model clients setup (following source project pattern)
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")
grok_api_key = os.getenv("GROK_API_KEY")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
GROK_BASE_URL = "https://api.x.ai/v1"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Initialize clients only if API keys are available
openrouter_client = AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=openrouter_api_key) if openrouter_api_key else None
deepseek_client = AsyncOpenAI(base_url=DEEPSEEK_BASE_URL, api_key=deepseek_api_key) if deepseek_api_key else None
grok_client = AsyncOpenAI(base_url=GROK_BASE_URL, api_key=grok_api_key) if grok_api_key else None
gemini_client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=google_api_key) if google_api_key else None

def get_model(model_name: str):
    """Get model client based on model name (following source project pattern)"""
    if "/" in model_name and openrouter_client:
        return OpenAIChatCompletionsModel(model=model_name, openai_client=openrouter_client)
    elif "deepseek" in model_name and deepseek_client:
        return OpenAIChatCompletionsModel(model=model_name, openai_client=deepseek_client)
    elif "grok" in model_name and grok_client:
        return OpenAIChatCompletionsModel(model=model_name, openai_client=grok_client)
    elif "gemini" in model_name and gemini_client:
        return OpenAIChatCompletionsModel(model=model_name, openai_client=gemini_client)
    else:
        # Default to standard OpenAI model name for OpenAI Agents SDK
        return model_name

@dataclass
class AgentConfig:
    """Configuration for trading agents using OpenAI Agents SDK"""
    name: str
    personality: str
    risk_tolerance: str  # "conservative", "moderate", "aggressive"
    initial_balance: float
    model_name: str = "gpt-4o-mini"
    max_turns: int = 30

@dataclass
class TradingDecision:
    """Represents a trading decision made by an agent"""
    action: str  # "buy", "sell", "hold"
    symbol: str
    quantity: int
    reasoning: str
    confidence: float  # 0.0 to 1.0
    timestamp: datetime
    current_price: float

class BaseAgent(ABC):
    """Base class for all trading agents using OpenAI Agents SDK"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent: Optional[Agent] = None
        self.trading_history: List[TradingDecision] = []
        
        # MCP server parameters (will be set by subclasses)
        self.trader_mcp_server_params = []
        self.researcher_mcp_server_params = []
    
    @abstractmethod
    def get_personality_instructions(self) -> str:
        """Get personality-specific instructions for the agent"""
        pass
    
    @abstractmethod
    def get_trader_mcp_server_params(self) -> List[Dict[str, Any]]:
        """Get MCP server parameters for trader tools"""
        pass
    
    @abstractmethod
    def get_researcher_mcp_server_params(self) -> List[Dict[str, Any]]:
        """Get MCP server parameters for researcher tools"""
        pass
    
    async def get_researcher_tool(self, researcher_mcp_servers, model_name) -> Tool:
        """Create researcher tool following source project pattern"""
        from researcher import get_researcher_tool
        return await get_researcher_tool(researcher_mcp_servers, model_name)
    
    async def create_agent(self, trader_mcp_servers, researcher_mcp_servers) -> Agent:
        """Create the OpenAI Agents SDK agent"""
        # Get researcher tool
        researcher_tool = await self.get_researcher_tool(researcher_mcp_servers, self.config.model_name)
        
        # Create agent with personality instructions
        instructions = self.get_personality_instructions()
        
        self.agent = Agent(
            name=self.config.name,
            instructions=instructions,
            model=get_model(self.config.model_name),
            tools=[researcher_tool],
            mcp_servers=trader_mcp_servers,
        )
        return self.agent
    
    async def get_account_report(self) -> str:
        """Get account report using MCP resource"""
        from accounts_client import read_accounts_resource
        account = await read_accounts_resource(self.config.name)
        account_json = json.loads(account)
        account_json.pop("portfolio_value_time_series", None)
        return json.dumps(account_json)
    
    async def get_strategy_report(self) -> str:
        """Get strategy report using MCP resource"""
        from accounts_client import read_strategy_resource
        return await read_strategy_resource(self.config.name)
    
    def get_trade_message(self, strategy: str, account: str) -> str:
        """Generate trading message following source project pattern"""
        return f"""Based on your investment strategy, you should now look for new opportunities.
Use the research tool to find news and opportunities consistent with your strategy.
Use the tools to research stock price and other company information.
Finally, make your decision, then execute trades using the tools.
Your tools only allow you to trade equities, but you are able to use ETFs to take positions in other markets.
You do not need to rebalance your portfolio; you will be asked to do so later.
Just make trades based on your strategy as needed.

Your investment strategy:
{strategy}

Here is your current account:
{account}

Here is the current datetime:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Now, carry out analysis, make your decision and execute trades. Your account name is {self.config.name}.
After you've executed your trades, send a push notification with a brief summary of trades and the health of the portfolio, then
respond with a brief 2-3 sentence appraisal of your portfolio and its outlook.
"""
    
    def get_rebalance_message(self, strategy: str, account: str) -> str:
        """Generate rebalancing message following source project pattern"""
        return f"""Based on your investment strategy, you should now examine your portfolio and decide if you need to rebalance.
Use the research tool to find news and opportunities affecting your existing portfolio.
Use the tools to research stock price and other company information affecting your existing portfolio.
Finally, make your decision, then execute trades using the tools as needed.
You do not need to identify new investment opportunities at this time; you will be asked to do so later.
Just rebalance your portfolio based on your strategy as needed.

Your investment strategy:
{strategy}

You also have a tool to change your strategy if you wish; you can decide at any time that you would like to evolve or even switch your strategy.

Here is your current account:
{account}

Here is the current datetime:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Now, carry out analysis, make your decision and execute trades. Your account name is {self.config.name}.
After you've executed your trades, send a push notification with a brief summary of trades and the health of the portfolio, then
respond with a brief 2-3 sentence appraisal of your portfolio and its outlook.
"""
    
    async def run_agent(self, trader_mcp_servers, researcher_mcp_servers, do_trade: bool = True):
        """Run the agent following source project pattern"""
        # Create agent
        self.agent = await self.create_agent(trader_mcp_servers, researcher_mcp_servers)
        
        # Get account and strategy
        account = await self.get_account_report()
        strategy = await self.get_strategy_report()
        
        # Generate message
        message = (
            self.get_trade_message(strategy, account)
            if do_trade
            else self.get_rebalance_message(strategy, account)
        )
        
        # Run agent
        await Runner.run(self.agent, message, max_turns=self.config.max_turns)
    
    async def run_with_mcp_servers(self, do_trade: bool = True):
        """Run agent with MCP servers following source project pattern"""
        async with AsyncExitStack() as stack:
            trader_mcp_servers = [
                await stack.enter_async_context(
                    MCPServerStdio(params, client_session_timeout_seconds=120)
                )
                for params in self.get_trader_mcp_server_params()
            ]
            
            async with AsyncExitStack() as stack:
                researcher_mcp_servers = [
                    await stack.enter_async_context(
                        MCPServerStdio(params, client_session_timeout_seconds=120)
                    )
                    for params in self.get_researcher_mcp_server_params()
                ]
                
                await self.run_agent(trader_mcp_servers, researcher_mcp_servers, do_trade)
    
    async def run_with_trace(self, do_trade: bool = True):
        """Run agent with tracing following source project pattern"""
        from tracers import make_trace_id
        
        trace_name = f"{self.config.name}-trading" if do_trade else f"{self.config.name}-rebalancing"
        trace_id = make_trace_id(f"{self.config.name.lower()}")
        
        with trace(trace_name, trace_id=trace_id):
            await self.run_with_mcp_servers(do_trade)
    
    async def run(self, do_trade: bool = True):
        """Main run method following source project pattern"""
        try:
            await self.run_with_trace(do_trade)
        except Exception as e:
            print(f"Error running trader {self.config.name}: {e}")
    
    async def run_with_custom_message(self, message: str):
        """Run agent with custom message for testing purposes"""
        try:
            async with AsyncExitStack() as stack:
                trader_mcp_servers = [
                    await stack.enter_async_context(
                        MCPServerStdio(params, client_session_timeout_seconds=120)
                    )
                    for params in self.get_trader_mcp_server_params()
                ]
                
                async with AsyncExitStack() as stack:
                    researcher_mcp_servers = [
                        await stack.enter_async_context(
                            MCPServerStdio(params, client_session_timeout_seconds=120)
                        )
                        for params in self.get_researcher_mcp_server_params()
                    ]
                    
                    # Create agent
                    self.agent = await self.create_agent(trader_mcp_servers, researcher_mcp_servers)
                    
                    # Run with custom message
                    await Runner.run(self.agent, message, max_turns=self.config.max_turns)
        except Exception as e:
            print(f"Error running trader {self.config.name} with custom message: {e}")
            raise
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for this agent"""
        if not self.trading_history:
            return {"total_trades": 0, "performance": "No trades yet"}
        
        total_trades = len(self.trading_history)
        buy_trades = len([t for t in self.trading_history if t.action == "buy"])
        sell_trades = len([t for t in self.trading_history if t.action == "sell"])
        avg_confidence = sum(t.confidence for t in self.trading_history) / total_trades
        
        return {
            "total_trades": total_trades,
            "buy_trades": buy_trades,
            "sell_trades": sell_trades,
            "average_confidence": round(avg_confidence, 2),
            "recent_trades": [
                {
                    "action": t.action,
                    "symbol": t.symbol,
                    "quantity": t.quantity,
                    "price": t.current_price,
                    "timestamp": t.timestamp.isoformat()
                }
                for t in self.trading_history[-5:]  # Last 5 trades
            ]
        }