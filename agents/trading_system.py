#!/usr/bin/env python3

import asyncio
import logging
from typing import List, Dict, Any

from simple_trader import SimpleTrader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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