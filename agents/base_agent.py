#!/usr/bin/env python3

<<<<<<< HEAD
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
=======
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import openai
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AgentConfig:
    """Configuration for trading agents"""
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2
    name: str
    personality: str
    risk_tolerance: str  # "conservative", "moderate", "aggressive"
    initial_balance: float
<<<<<<< HEAD
    model_name: str = "gpt-4o-mini"
    max_turns: int = 30
=======
    openai_model: str = "gpt-4"
    max_tokens: int = 2000
    temperature: float = 0.7
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2

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
<<<<<<< HEAD
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
=======
    """Base class for all trading agents"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.account_id = None
        self.trading_history: List[TradingDecision] = []
        
        # MCP tool connections (will be injected)
        self.accounts_tools = None
        self.market_tools = None
        self.push_tools = None
        self.memory_tools = None
        self.researcher_tool = None
    
    def set_mcp_tools(self, accounts_tools, market_tools, push_tools, memory_tools=None, researcher_tool=None):
        """Inject MCP tool connections"""
        self.accounts_tools = accounts_tools
        self.market_tools = market_tools
        self.push_tools = push_tools
        self.memory_tools = memory_tools
        self.researcher_tool = researcher_tool
    
    async def initialize_account(self) -> str:
        """Initialize trading account for this agent"""
        if not self.accounts_tools:
            raise RuntimeError("MCP tools not configured")
        
        # Create account with agent's personality as strategy
        self.account_id = await self.accounts_tools.create_account(
            name=self.config.name,
            initial_balance=self.config.initial_balance,
            strategy=self.config.personality
        )
        
        logger.info(f"Agent {self.config.name} initialized with account {self.account_id}")
        return self.account_id
    
    async def get_account_balance(self) -> float:
        """Get current account balance"""
        if not self.account_id:
            await self.initialize_account()
        
        balance_info = await self.accounts_tools.get_balance(self.account_id)
        return balance_info['cash_balance']
    
    async def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        if not self.account_id:
            await self.initialize_account()
        
        balance_info = await self.accounts_tools.get_balance(self.account_id)
        return balance_info['total_value']
    
    async def get_holdings(self) -> Dict[str, Any]:
        """Get current stock holdings"""
        if not self.account_id:
            await self.initialize_account()
        
        return await self.accounts_tools.get_holdings(self.account_id)
    
    async def execute_trade(self, decision: TradingDecision) -> bool:
        """Execute a trading decision"""
        try:
            if decision.action == "buy":
                result = await self.accounts_tools.buy_shares(
                    account_id=self.account_id,
                    symbol=decision.symbol,
                    quantity=decision.quantity
                )
            elif decision.action == "sell":
                result = await self.accounts_tools.sell_shares(
                    account_id=self.account_id,
                    symbol=decision.symbol,
                    quantity=decision.quantity
                )
            else:  # hold
                logger.info(f"Agent {self.config.name} decided to hold {decision.symbol}")
                return True
            
            # Log the trade
            self.trading_history.append(decision)
            
            # Store trading decision in memory
            if self.memory_tools:
                try:
                    await self.memory_tools.store_trading_decision(
                        symbol=decision.symbol,
                        action=decision.action,
                        reasoning=decision.reasoning,
                        price=decision.current_price,
                        quantity=decision.quantity
                    )
                    logger.info(f"Stored trading decision in memory for {decision.symbol}")
                except Exception as e:
                    logger.warning(f"Failed to store trading decision in memory: {e}")
            
            # Send notification
            if self.push_tools:
                await self.push_tools.send_notification(
                    f"Agent {self.config.name}: {decision.action.upper()} {decision.quantity} shares of {decision.symbol} at ${decision.current_price:.2f}"
                )
            
            logger.info(f"Trade executed: {decision.action} {decision.quantity} {decision.symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            return False
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive market data for a symbol with data quality awareness"""
        # Get enhanced data with metadata
        try:
            price_data = await self.market_tools.get_price_with_metadata(symbol)
            indicators_data = await self.market_tools.get_market_indicators_with_metadata(symbol)
            trend_analysis = await self.market_tools.analyze_stock_trend(symbol)
            
            return {
                "current_price": price_data["price"],
                "price_metadata": {
                    "data_tier": price_data["data_tier"],
                    "data_age_minutes": price_data["data_age_minutes"],
                    "data_source": price_data["data_source"]
                },
                "indicators": indicators_data["indicators"],
                "indicators_metadata": {
                    "data_tier": indicators_data["data_tier"],
                    "warning": indicators_data.get("warning")
                },
                "trend_analysis": trend_analysis,
                "data_quality_summary": self._assess_data_quality(price_data, indicators_data, trend_analysis)
            }
        except Exception as e:
            # Fallback to basic data if enhanced methods fail
            logger.warning(f"Enhanced data retrieval failed for {symbol}, falling back to basic data: {e}")
            current_price = await self.market_tools.lookup_share_price(symbol)
            indicators = await self.market_tools.get_market_indicators(symbol)
            trend_analysis = await self.market_tools.analyze_stock_trend(symbol)
            
            return {
                "current_price": current_price,
                "price_metadata": {"data_tier": "UNKNOWN", "warning": "Using fallback data"},
                "indicators": indicators,
                "indicators_metadata": {"data_tier": "UNKNOWN"},
                "trend_analysis": trend_analysis,
                "data_quality_summary": "Data quality information unavailable - using fallback methods"
            }
    
    def _assess_data_quality(self, price_data: Dict, indicators_data: Dict, trend_analysis: Dict) -> str:
        """Assess overall data quality and provide summary"""
        issues = []
        
        # Check price data quality
        if price_data["data_tier"] == "MOCK":
            issues.append("Price data is simulated")
        elif price_data["data_age_minutes"] > 60:
            issues.append(f"Price data is {price_data['data_age_minutes']} minutes old")
        
        # Check for warnings
        if indicators_data.get("warning"):
            issues.append("Indicators may be unreliable")
        
        # Check trend analysis warnings
        if trend_analysis.get("data_quality", {}).get("warnings"):
            issues.extend(trend_analysis["data_quality"]["warnings"])
        
        if not issues:
            return "Data quality is good for trading decisions"
        else:
            return f"Data quality concerns: {'; '.join(issues)}"
    
    async def get_memory_context(self, symbol: str) -> str:
        """Retrieve relevant memory context for trading decision"""
        if not self.memory_tools:
            return "No memory system available."
        
        try:
            # Get past decisions for this symbol
            past_decisions = await self.memory_tools.retrieve_past_decisions(symbol)
            
            # Get past market analysis for this symbol
            past_analysis = await self.memory_tools.retrieve_market_insights(symbol)
            
            # Get general trading insights
            general_insights = await self.memory_tools.retrieve_past_decisions()
            
            memory_context = f"""
MEMORY CONTEXT FROM KNOWLEDGE GRAPH:

Past Trading Decisions for {symbol}:
{past_decisions if past_decisions else "No previous decisions found for this symbol."}

Past Market Analysis for {symbol}:
{past_analysis if past_analysis else "No previous analysis found for this symbol."}

Recent General Trading Insights:
{general_insights if general_insights else "No general insights available."}

Use this historical context to inform your current decision. Learn from past successes and mistakes.
"""
            return memory_context
            
        except Exception as e:
            logger.warning(f"Failed to retrieve memory context: {e}")
            return "Memory context unavailable due to error."
    
    async def store_market_analysis_in_memory(self, symbol: str, market_data: Dict[str, Any], reasoning: str):
        """Store market analysis in memory for future reference"""
        if not self.memory_tools:
            return
        
        try:
            analysis_summary = f"""
Market Analysis Summary:
- Current Price: ${market_data['current_price']:.2f}
- Trend: {market_data['trend_analysis']['trend']}
- Price Change: {market_data['trend_analysis']['price_change_percent']:.2f}%
- Data Quality: {market_data.get('data_quality_summary', 'Unknown')}
- Agent Reasoning: {reasoning}
"""
            
            await self.memory_tools.store_market_analysis(
                symbol=symbol,
                analysis=analysis_summary,
                indicators=market_data['indicators']
            )
            logger.info(f"Stored market analysis in memory for {symbol}")
            
        except Exception as e:
            logger.warning(f"Failed to store market analysis in memory: {e}")
    
    async def get_research_insights(self, symbol: str) -> str:
        """Get research insights for a symbol using the researcher tool"""
        if not self.researcher_tool:
            return "No researcher tool available."
        
        try:
            # Create research request
            research_request = f"Research financial news and market sentiment for {symbol}. Include recent developments, analyst opinions, and potential trading opportunities or risks."
            
            # Call researcher tool
            research_result = await self.researcher_tool['function'](research_request)
            
            logger.info(f"Retrieved research insights for {symbol}")
            return research_result
            
        except Exception as e:
            logger.warning(f"Failed to get research insights for {symbol}: {e}")
            return f"Research unavailable due to error: {str(e)}"
    
    async def generate_trading_prompt(self, symbol: str, market_data: Dict[str, Any]) -> str:
        """Generate the prompt for OpenAI based on agent personality and market data"""
        
        # Get current portfolio state
        balance = await self.get_account_balance()
        holdings = await self.get_holdings()
        portfolio_value = await self.get_portfolio_value()
        
        # Extract data quality information
        price_metadata = market_data.get('price_metadata', {})
        indicators_metadata = market_data.get('indicators_metadata', {})
        data_quality_summary = market_data.get('data_quality_summary', 'Data quality unknown')
        
        # Base prompt with agent personality and enhanced data awareness
        prompt = f"""
You are {self.config.name}, a trading agent with a {self.config.personality} investment personality and {self.config.risk_tolerance} risk tolerance.

CURRENT PORTFOLIO STATUS:
- Cash Balance: ${balance:.2f}
- Total Portfolio Value: ${portfolio_value:.2f}
- Current Holdings: {json.dumps(holdings, indent=2)}

MARKET DATA FOR {symbol}:
- Current Price: ${market_data['current_price']:.2f}
- SMA5: ${market_data['indicators']['sma5']:.2f}
- SMA20: ${market_data['indicators']['sma20']:.2f}
- Volatility: {market_data['indicators']['volatility']:.2f}
- Trend: {market_data['trend_analysis']['trend']}
- Price Change: {market_data['trend_analysis']['price_change_percent']:.2f}%

DATA QUALITY ASSESSMENT:
- Price Data Tier: {price_metadata.get('data_tier', 'UNKNOWN')}
- Data Age: {price_metadata.get('data_age_minutes', 'Unknown')} minutes
- Data Source: {price_metadata.get('data_source', 'Unknown')}
- Quality Summary: {data_quality_summary}
- Indicators Warning: {indicators_metadata.get('warning', 'None')}

IMPORTANT DATA QUALITY CONSIDERATIONS:
- If data tier is "MOCK" or "Simulated", this is test data - be extremely cautious
- If data age is >60 minutes, consider the staleness in your decision
- If there are quality warnings, factor them into your confidence level
- Real trading decisions should only be made with reliable, fresh data

{self.get_personality_prompt()}

MEMORY AND LEARNING CONTEXT:
{await self.get_memory_context(symbol)}

RESEARCH INSIGHTS:
{await self.get_research_insights(symbol)}

Based on this information, make a trading decision for {symbol}. Consider:
1. Your investment personality and risk tolerance
2. Current market conditions and technical indicators
3. Your existing portfolio allocation
4. Position sizing appropriate for your risk level
5. **DATA QUALITY**: Factor data freshness and reliability into your decision
6. **RISK ADJUSTMENT**: Lower confidence if data quality is poor
7. **HISTORICAL LEARNING**: Use memory context to learn from past decisions and analysis
8. **PATTERN RECOGNITION**: Identify patterns from your trading history
9. **RESEARCH INSIGHTS**: Factor in recent news, market sentiment, and analyst opinions from research

Respond with a JSON object containing:
{{
    "action": "buy" | "sell" | "hold",
    "quantity": <number of shares>,
    "reasoning": "<detailed explanation including data quality considerations>",
    "confidence": <0.0 to 1.0, adjusted for data quality>
}}

If buying, ensure you have sufficient cash. If selling, ensure you own the stock.
CRITICAL: If data tier is MOCK or data is very stale, strongly consider "hold" action.
"""
        return prompt
    
    @abstractmethod
    def get_personality_prompt(self) -> str:
        """Get personality-specific prompt additions"""
        pass
    
    async def make_trading_decision(self, symbol: str) -> TradingDecision:
        """Make a trading decision using OpenAI"""
        try:
            # Get market data
            market_data = await self.get_market_data(symbol)
            
            # Generate prompt
            prompt = await self.generate_trading_prompt(symbol, market_data)
            
            # Call OpenAI
            response = self.client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": "You are a professional trading agent. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            # Parse response
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            decision_data = json.loads(response_text)
            
            # Create TradingDecision object
            decision = TradingDecision(
                action=decision_data["action"],
                symbol=symbol,
                quantity=decision_data.get("quantity", 0),
                reasoning=decision_data["reasoning"],
                confidence=decision_data["confidence"],
                timestamp=datetime.now(),
                current_price=market_data["current_price"]
            )
            
            # Store market analysis in memory for future learning
            await self.store_market_analysis_in_memory(symbol, market_data, decision.reasoning)
            
            logger.info(f"Agent {self.config.name} decision for {symbol}: {decision.action} (confidence: {decision.confidence:.2f})")
            return decision
            
        except Exception as e:
            logger.error(f"Error making trading decision: {e}")
            # Return a safe "hold" decision
            return TradingDecision(
                action="hold",
                symbol=symbol,
                quantity=0,
                reasoning=f"Error in decision making: {str(e)}",
                confidence=0.0,
                timestamp=datetime.now(),
                current_price=market_data.get("current_price", 0.0) if 'market_data' in locals() else 0.0
            )
    
    async def run_trading_cycle(self, symbols: List[str]) -> List[TradingDecision]:
        """Run a complete trading cycle for given symbols"""
        decisions = []
        
        logger.info(f"Agent {self.config.name} starting trading cycle for {len(symbols)} symbols")
        
        for symbol in symbols:
            try:
                decision = await self.make_trading_decision(symbol)
                decisions.append(decision)
                
                # Execute the trade if not holding
                if decision.action != "hold":
                    await self.execute_trade(decision)
                
                # Small delay between decisions
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue
        
        return decisions
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2
    
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