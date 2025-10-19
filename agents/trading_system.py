#!/usr/bin/env python3

import asyncio
import aiohttp
import logging
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

from simple_trader import SimpleTrader

# Load environment variables
load_dotenv(override=True)

# Configuration
RUN_EVERY_N_MINUTES = int(os.getenv("RUN_EVERY_N_MINUTES", "60"))

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

async def check_market_status() -> bool:
    """Check if market is open via backend API"""
    try:
        base_url = os.getenv("BACKEND_URL", "http://backend-service:8080")
        url = f"{base_url}/api/market/status"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    result = await response.json()
                    # Backend returns wrapped format: {"success": true, "data": {...}}
                    if result.get("success") and result.get("data"):
                        data = result["data"]
                        is_open = data.get("status") == "OPEN"
                        logger.info(f"📊 Market status: {data.get('status')} - {data.get('nextEvent')}")
                        return is_open
                    else:
                        logger.error(f"API returned error: {result.get('error')}")
                        return False
                else:
                    logger.error(f"Failed to check market status: HTTP {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Error checking market status: {e}")
        return False

async def update_all_agents_activity():
    """Update lastActivity for all agents (called on every cycle, even when market closed)"""
    agent_names = ["Warren", "George", "Ray", "Cathie"]
    base_url = os.getenv("BACKEND_URL", "http://backend-service:8080")
    url = f"{base_url}/api/accounts/tools/update_activity"

    try:
        async with aiohttp.ClientSession() as session:
            for agent_name in agent_names:
                try:
                    async with session.post(url, json={"name": agent_name}) as response:
                        if response.status == 200:
                            logger.debug(f"✓ Updated activity for {agent_name}")
                        else:
                            logger.warning(f"Failed to update activity for {agent_name}: {response.status}")
                except Exception as e:
                    logger.warning(f"Error updating activity for {agent_name}: {e}")
    except Exception as e:
        logger.error(f"Error updating agents activity: {e}")

async def run_continuous_trading():
    """Run continuous trading cycles - matches source project pattern"""
    system = TradingSystem()

    print(f"🔄 Starting scheduler to run every {RUN_EVERY_N_MINUTES} minutes")
    logger.info(f"Continuous trading loop started with {RUN_EVERY_N_MINUTES} minute intervals")
    logger.info("Market hours check: ALWAYS ENABLED (saves API costs)")

    try:
        while True:
            # Always check market status before running agents to save API costs
            is_market_open = await check_market_status()

            if not is_market_open:
                logger.info("⏸️  Market is closed. Skipping trading cycle to save API costs.")
            else:
                logger.info("🚀 Starting new trading cycle...")
                await system.run_all_agents()
                logger.info(f"✅ Trading cycle completed.")

            # Always update activity timestamp on every cycle (shows system is alive)
            await update_all_agents_activity()
            logger.info(f"💤 Waiting {RUN_EVERY_N_MINUTES} minutes until next cycle...")
            await asyncio.sleep(RUN_EVERY_N_MINUTES * 60)
    except KeyboardInterrupt:
        logger.info("🛑 Graceful shutdown requested (Ctrl+C)")
        print("\n🛑 Shutting down trading system gracefully...")
    except Exception as e:
        logger.error(f"❌ Trading system error: {e}")
        raise

async def main():
    """Main function - single run for testing"""
    logger.info("🚀 Starting Agentic Trading System (single run)...")
    
    try:
        system = TradingSystem()
        await system.run_all_agents()
        logger.info("✅ Trading system completed successfully")
    except Exception as e:
        logger.error(f"❌ Trading system failed: {e}")
        raise

if __name__ == "__main__":
    # Check if we should run continuously or just once
    continuous_mode = os.getenv("CONTINUOUS_MODE", "true").lower() == "true"
    
    if continuous_mode:
        print("🔄 Running in CONTINUOUS mode")
        asyncio.run(run_continuous_trading())
    else:
        print("🎯 Running in SINGLE mode")
        asyncio.run(main())