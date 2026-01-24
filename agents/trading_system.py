#!/usr/bin/env python3

import asyncio
import aiohttp
import logging
import os
from contextlib import AsyncExitStack
from typing import List
from dotenv import load_dotenv

from agents.mcp import MCPServerStdio
from simple_trader import SimpleTrader
from config import BACKEND_API_AGENTS
from api_server import TradingAPIServer
from mcp_types import MCPName, MCPPool
from mcp_params import get_mcp_server_params

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
        """Factory method: fetch agent data from backend API."""
        # Fetch agent data from backend (includes id, name, style, strategy)
        async with aiohttp.ClientSession() as session:
            async with session.get(BACKEND_API_AGENTS) as response:
                if response.status != 200:
                    raise RuntimeError(f"Failed to load agents registry (status {response.status})")
                data = await response.json()
        
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        
        # Create traders from backend data
        agents = []
        for agent_data in data:
            agent_id = agent_data.get("id")
            name = agent_data.get("name")
            style = agent_data.get("style") or "Investor"
            strategy = agent_data.get("strategy") or ""  # Strategy description from DB
            
            if agent_id is None or name is None:
                logger.warning(f"Skipping agent with missing id or name: {agent_data}")
                continue
            
            agents.append(SimpleTrader(name, style, strategy, agent_id=agent_id))
            logger.info(f"✓ Created {name} ({style}) with agent ID {agent_id}")
        
        if not agents:
            raise RuntimeError("No agents loaded from backend API")
        
        logger.info(f"✅ TradingSystem created with {len(agents)} agents")
        return cls(agents)
    
    async def run_all_agents(self, force_one_trade=False):
        """Run all four agents concurrently

        Args:
            force_one_trade: If True, randomly pick one agent to force a trade
        """
        logger.info("🚀 Starting all four autonomous trading agents...")

        # Print agent summary
        self.print_agent_summary()

        # If manual trigger, force one random agent to trade
        forced_agent = None
        if force_one_trade:
            import random
            forced_agent = random.choice(self.agents).name
            logger.info(f"🎯 Manual trigger: Forcing {forced_agent} to make a trade this cycle")

        # Create MCP pool for this trading cycle
        async with AsyncExitStack() as stack:
            # Get MCP server configurations
            mcp_params = get_mcp_server_params()

            # Create pool: MCPName -> ServerSession
            mcp_pool: MCPPool = {}
            for mcp_name, params in mcp_params.items():
                server = await stack.enter_async_context(
                    MCPServerStdio(params, client_session_timeout_seconds=120)
                )
                mcp_pool[mcp_name] = server

            logger.info(f"✅ MCP pool created with {len(mcp_pool)} servers: {list(mcp_pool.keys())}")

            # Run all agents concurrently with shared MCP pool
            tasks = [
                agent.run(mcp_pool, force_trade=(agent.name == forced_agent))
                for agent in self.agents
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("✅ All agents completed their trading cycle")
    
    def print_agent_summary(self):
        """Print a summary of all agents"""
        print("\n" + "="*80)
        print("🏛️  AGENTIC TRADING SYSTEM - AGENT ROSTER")
        print("="*80)
        
        # Use actual agent data from self.agents
        for agent in self.agents:
            print(f"👤 {agent.name} ({agent.agent_style})")
            print()
        
        print("="*80 + "\n")

async def update_all_agents_activity():
    """Update lastActivity for all agents (called on every cycle, even when market closed)"""
    from config import BACKEND_API_ACCOUNTS, BACKEND_API_AGENTS

    try:
        async with aiohttp.ClientSession() as session:
            # Fetch all agents from backend
            async with session.get(BACKEND_API_AGENTS) as response:
                response.raise_for_status()
                agent_registry = await response.json()

            if isinstance(agent_registry, dict) and "data" in agent_registry:
                agent_registry = agent_registry["data"]

            if not isinstance(agent_registry, list):
                raise RuntimeError("Unexpected agent registry payload")

            # Update activity for all agents in registry
            for agent_data in agent_registry:
                agent_id = agent_data.get("id")
                agent_name = agent_data.get("name")
                
                if agent_id is None:
                    logger.warning(f"Skipping activity update for agent with missing id: {agent_data}")
                    continue

                try:
                    # Use new REST endpoint: PUT /api/accounts/{agentId}/activity
                    update_url = f"{BACKEND_API_ACCOUNTS}/{agent_id}/activity"
                    async with session.put(update_url) as response:
                        if response.status == 204:
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

    # Create flag to track if a cycle is currently running (thread-safe dict)
    cycle_running_flag = {'running': False}

    # Start the API server for manual cycle triggers (proper encapsulation, no globals!)
    api_server = TradingAPIServer(
        trading_system=system,
        manual_cycle_event=manual_cycle_event,
        cycle_running_flag=cycle_running_flag
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

            is_manual_trigger = False
            try:
                # Wait for manual trigger with timeout (scheduled interval)
                await asyncio.wait_for(manual_cycle_event.wait(), timeout=sleep_seconds)
                # Manual trigger received!
                logger.info("📣 Manual cycle triggered - starting immediately...")
                manual_cycle_event.clear()  # Reset for next trigger
                is_manual_trigger = True
            except asyncio.TimeoutError:
                # Normal scheduled cycle
                logger.info("⏰ Scheduled cycle time reached")

            # Always run trading cycle (demo system with end-of-day data)
            logger.info("🚀 Starting trading cycle...")

            # Set flag to indicate cycle is running
            cycle_running_flag['running'] = True

            try:
                # Force one agent to trade if manually triggered
                await system.run_all_agents(force_one_trade=is_manual_trigger)
                logger.info(f"✅ Trading cycle completed.")

                # Always update activity timestamp on every cycle (shows system is alive)
                await update_all_agents_activity()
            finally:
                # Always clear the flag, even if there was an error
                cycle_running_flag['running'] = False
                logger.info("🔓 Trading cycle lock released")
            
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