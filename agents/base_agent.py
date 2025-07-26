#!/usr/bin/env python3

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
    name: str
    personality: str
    risk_tolerance: str  # "conservative", "moderate", "aggressive"
    initial_balance: float
    openai_model: str = "gpt-4"
    max_tokens: int = 2000
    temperature: float = 0.7

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
    
    def set_mcp_tools(self, accounts_tools, market_tools, push_tools):
        """Inject MCP tool connections"""
        self.accounts_tools = accounts_tools
        self.market_tools = market_tools
        self.push_tools = push_tools
    
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
        """Get comprehensive market data for a symbol"""
        current_price = await self.market_tools.lookup_share_price(symbol)
        indicators = await self.market_tools.get_market_indicators(symbol)
        trend_analysis = await self.market_tools.analyze_stock_trend(symbol)
        
        return {
            "current_price": current_price,
            "indicators": indicators,
            "trend_analysis": trend_analysis
        }
    
    async def generate_trading_prompt(self, symbol: str, market_data: Dict[str, Any]) -> str:
        """Generate the prompt for OpenAI based on agent personality and market data"""
        
        # Get current portfolio state
        balance = await self.get_account_balance()
        holdings = await self.get_holdings()
        portfolio_value = await self.get_portfolio_value()
        
        # Base prompt with agent personality
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

{self.get_personality_prompt()}

Based on this information, make a trading decision for {symbol}. Consider:
1. Your investment personality and risk tolerance
2. Current market conditions and technical indicators
3. Your existing portfolio allocation
4. Position sizing appropriate for your risk level

Respond with a JSON object containing:
{{
    "action": "buy" | "sell" | "hold",
    "quantity": <number of shares>,
    "reasoning": "<detailed explanation of your decision>",
    "confidence": <0.0 to 1.0>
}}

If buying, ensure you have sufficient cash. If selling, ensure you own the stock.
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