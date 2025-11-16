#!/usr/bin/env python3

import asyncio
import aiohttp
import logging
import os
from typing import List
from dotenv import load_dotenv

from simple_trader import SimpleTrader
from config import BACKEND_API_AGENTS
from api_server import TradingAPIServer

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
    
    def __init__(self, agents: List[SimpleTrader]):
        """Initialize with pre-configured agents (use create() factory method)"""
        self.agents = agents
    
    @classmethod
    async def create(cls):
        """Factory method: fetch agent IDs once, then create traders with IDs."""
        # Single API call to convert names to IDs
        async with aiohttp.ClientSession() as session:
            async with session.get(BACKEND_API_AGENTS) as response:
                if response.status != 200:
                    raise RuntimeError(f"Failed to load agents registry (status {response.status})")
                data = await response.json()
        
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        
        # Create name -> id mapping (one-time conversion)
        name_to_id = {agent.get("name"): agent.get("id") for agent in data}
        
        # Create traders with IDs already set (no name lookup needed later)
        agent_configs = [
            ("Warren", """
You are Warren, and you are named in homage to your role model, Warren Buffett.
You are a value-oriented investor who prioritizes long-term wealth creation.
You identify high-quality companies trading below their intrinsic value.
You invest patiently and hold positions through market fluctuations, 
relying on meticulous fundamental analysis, steady cash flows, strong management teams, 
and competitive advantages. You rarely react to short-term market movements, 
trusting your deep research and value-driven strategy.
"""),
            ("George", """
You are George, and you are named in homage to your role model, George Soros.
You are a contrarian macro investor who focuses on large-scale economic and political trends.
You use reflexivity theory to identify market inefficiencies and bubbles.
You're willing to take large, concentrated positions when you have high conviction,
and you're not afraid to go against conventional wisdom. You focus on currencies,
commodities, and broad market movements, looking for paradigm shifts and market dislocations.
"""),
            ("Ray", """
You are Ray, and you are named in homage to your role model, Ray Dalio.
You are a systematic investor who focuses on risk parity and diversification.
You believe in building all-weather portfolios that can perform across different economic environments.
You use systematic approaches, focus on uncorrelated returns, and emphasize risk management.
You look for balance across asset classes and economic regimes, preferring steady,
risk-adjusted returns over high-risk, high-reward strategies.
"""),
            ("Cathie", """
You are Cathie, and you are named in homage to your role model, Cathie Wood.
You are a growth investor focused on disruptive innovation and exponential technologies.
You invest in companies that are transforming industries through artificial intelligence,
robotics, autonomous vehicles, blockchain, and other breakthrough technologies.
You have a long-term investment horizon and are willing to accept high volatility
in exchange for the potential of exponential returns from revolutionary companies.
""")
        ]
        
        agents = []
        for name, strategy in agent_configs:
            agent_id = name_to_id.get(name)
            if agent_id is None:
                raise RuntimeError(f"Agent id not found for name: {name}")
            agents.append(SimpleTrader(name, strategy, agent_id=agent_id))
            logger.info(f"✓ Created {name} with agent ID {agent_id}")
        
        logger.info("✅ TradingSystem created with all agent IDs resolved")
        return cls(agents)
    
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

async def update_all_agents_activity():
    """Update lastActivity for all agents (called on every cycle, even when market closed)"""
    agent_names = ["Warren", "George", "Ray", "Cathie"]
    from config import BACKEND_API_ACCOUNTS, BACKEND_API_AGENTS
    update_url = f"{BACKEND_API_ACCOUNTS}/tools/update_activity"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(BACKEND_API_AGENTS) as response:
                response.raise_for_status()
                agent_registry = await response.json()

            if isinstance(agent_registry, dict) and "data" in agent_registry:
                agent_registry = agent_registry["data"]

            if not isinstance(agent_registry, list):
                raise RuntimeError("Unexpected agent registry payload")

            name_to_id = {agent.get("name"): agent.get("id") for agent in agent_registry}

            for agent_name in agent_names:
                agent_id = name_to_id.get(agent_name)
                if agent_id is None:
                    logger.warning(f"Skipping activity update for {agent_name}: id not found in registry")
                    continue

                try:
                    async with session.post(update_url, json={"agentId": agent_id}) as response:
                        if response.status == 200:
                            logger.debug(f"✓ Updated activity for {agent_name} (id={agent_id})")
                        else:
                            logger.warning(f"Failed to update activity for {agent_name} (id={agent_id}): {response.status}")
                except Exception as e:
                    logger.warning(f"Error updating activity for {agent_name} (id={agent_id}): {e}")
    except Exception as e:
        logger.error(f"Error updating agents activity: {e}")

async def run_continuous_trading():
    """Run continuous trading cycles - matches source project pattern"""
    system = await TradingSystem.create()  # Single API call: names → IDs, then create with IDs
    
    # Create event for manual cycle triggers
    manual_cycle_event = asyncio.Event()
    
    # Start the API server for manual cycle triggers (proper encapsulation, no globals!)
    api_server = TradingAPIServer(
        trading_system=system,
        manual_cycle_event=manual_cycle_event
    )
    api_server.run(port=8000)

    print(f"🔄 Starting scheduler to run every {RUN_EVERY_N_MINUTES} minutes")
    logger.info(f"Continuous trading loop started with {RUN_EVERY_N_MINUTES} minute intervals")
    logger.info("🎓 Demo mode: Trading enabled 24/7 (using end-of-day data)")
    logger.info("📡 Manual cycle trigger available at http://localhost:8000/api/trigger-cycle")
    logger.info(f"⏰ First cycle will run in {RUN_EVERY_N_MINUTES} minutes or when manually triggered")
    logger.info(f"🔧 DEBUG: Event loop: {asyncio.get_event_loop()}")
    logger.info(f"🔧 DEBUG: Manual cycle event: {manual_cycle_event}")

    try:
        logger.info("🚀 Entering main trading loop...")
        while True:
            # Wait for either: scheduled time OR manual trigger event
            sleep_seconds = RUN_EVERY_N_MINUTES * 60
            logger.info(f"💤 Waiting {RUN_EVERY_N_MINUTES} minutes for next cycle (or manual trigger)...")
            
            try:
                # Wait for manual trigger with timeout (scheduled interval)
                await asyncio.wait_for(manual_cycle_event.wait(), timeout=sleep_seconds)
                # Manual trigger received!
                logger.info("📣 Manual cycle triggered - starting immediately...")
                manual_cycle_event.clear()  # Reset for next trigger
            except asyncio.TimeoutError:
                # Normal scheduled cycle
                logger.info("⏰ Scheduled cycle time reached")
            
            # Always run trading cycle (demo system with end-of-day data)
            logger.info("🚀 Starting trading cycle...")
            await system.run_all_agents()
            logger.info(f"✅ Trading cycle completed.")

            # Always update activity timestamp on every cycle (shows system is alive)
            await update_all_agents_activity()
            
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
        system = await TradingSystem.create()  # Single API call: names → IDs, then create with IDs
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