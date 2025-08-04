#!/usr/bin/env python3

import asyncio
import logging
<<<<<<< HEAD
from typing import List, Dict, Any
from datetime import datetime

=======
import json
from datetime import datetime
from typing import List, Dict, Any

from agent_orchestrator import AgentOrchestrator
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2
from warren_agent import create_warren_agent
from george_agent import create_george_agent
from ray_agent import create_ray_agent
from cathie_agent import create_cathie_agent
<<<<<<< HEAD
from tracers import LogTracer
from agents import add_trace_processor
=======
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingSystem:
    """
<<<<<<< HEAD
    SDK-based trading system using OpenAI Agents SDK following source project pattern
    """
    
    def __init__(self):
        self.agents = []
=======
    Main trading system that orchestrates all four autonomous agents
    """
    
    def __init__(self):
        self.orchestrator = AgentOrchestrator()
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2
        self.agents_initialized = False
        
        # Trading configuration
        self.trading_symbols = [
            "AAPL",   # Apple - Technology
            "GOOGL",  # Google - Technology/Innovation
            "MSFT",   # Microsoft - Technology/Cloud
            "TSLA",   # Tesla - Innovation/EV
            "AMZN",   # Amazon - E-commerce/Cloud
            "NVDA",   # NVIDIA - AI/Semiconductors
            "META",   # Meta - Social Media/VR
            "NFLX",   # Netflix - Streaming/Content
            "SPY",    # S&P 500 ETF - Market Index
            "QQQ"     # NASDAQ ETF - Tech Index
        ]
    
    async def initialize_system(self):
<<<<<<< HEAD
        """Initialize the SDK-based trading system with all four agents"""
        logger.info("🚀 Initializing SDK-based Agentic Trading System...")
        
        # Add trace processor
        add_trace_processor(LogTracer())
        
        # Create the four legendary traders using SDK
=======
        """Initialize the trading system with all four agents"""
        logger.info("🚀 Initializing Agentic Trading System...")
        
        # Create the four legendary traders
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2
        warren = create_warren_agent()
        george = create_george_agent()
        ray = create_ray_agent()
        cathie = create_cathie_agent()
        
<<<<<<< HEAD
        # Add agents to system
        self.agents = [warren, george, ray, cathie]
        
        self.agents_initialized = True
        logger.info("✅ SDK Trading system initialized with 4 autonomous agents")
=======
        # Add agents to orchestrator
        self.orchestrator.add_agent(warren)
        self.orchestrator.add_agent(george)
        self.orchestrator.add_agent(ray)
        self.orchestrator.add_agent(cathie)
        
        # Set trading symbols
        self.orchestrator.trading_symbols = self.trading_symbols
        
        # Initialize all agents
        await self.orchestrator.initialize_agents()
        
        self.agents_initialized = True
        logger.info("✅ Trading system initialized with 4 autonomous agents")
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2
        
        # Print agent summary
        self.print_agent_summary()
    
    def print_agent_summary(self):
        """Print a summary of all agents"""
        print("\n" + "="*80)
<<<<<<< HEAD
        print("🏛️  SDK-BASED AGENTIC TRADING SYSTEM - AGENT ROSTER")
=======
        print("🏛️  AGENTIC TRADING SYSTEM - AGENT ROSTER")
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2
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
        
        print(f"📈 Trading Universe: {', '.join(self.trading_symbols)}")
<<<<<<< HEAD
        print("🔧 Using OpenAI Agents SDK with MCP integration")
        print("="*80 + "\n")
    
    async def run_single_cycle(self, do_trade: bool = True) -> Dict[str, Any]:
        """Run a single trading cycle for all agents"""
        if not self.agents_initialized:
            await self.initialize_system()
        
        cycle_type = "trading" if do_trade else "rebalancing"
        logger.info(f"🔄 Running {cycle_type} cycle...")
        
        start_time = datetime.now()
        results = {
            "timestamp": start_time.isoformat(),
            "cycle_type": cycle_type,
            "agents": {},
            "total_agents": len(self.agents),
            "market_open": True  # Assume market is open for now
        }
        
        # Run all agents concurrently
        agent_tasks = []
        for agent in self.agents:
            task = asyncio.create_task(agent.run(do_trade=do_trade))
            agent_tasks.append((agent.config.name, task))
        
        # Wait for all agents to complete
        for agent_name, task in agent_tasks:
            try:
                await task
                results["agents"][agent_name] = {
                    "status": "completed",
                    "performance": self.agents[next(i for i, a in enumerate(self.agents) if a.config.name == agent_name)].get_performance_summary()
                }
                logger.info(f"✅ Agent {agent_name} completed {cycle_type} cycle")
            except Exception as e:
                logger.error(f"❌ Agent {agent_name} failed: {e}")
                results["agents"][agent_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        end_time = datetime.now()
        results["duration_seconds"] = (end_time - start_time).total_seconds()
=======
        print("="*80 + "\n")
    
    async def run_single_cycle(self) -> Dict[str, Any]:
        """Run a single trading cycle"""
        if not self.agents_initialized:
            await self.initialize_system()
        
        logger.info("🔄 Running trading cycle...")
        results = await self.orchestrator.run_single_cycle()
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2
        
        # Print cycle summary
        self.print_cycle_summary(results)
        
        return results
    
    def print_cycle_summary(self, results: Dict[str, Any]):
        """Print a summary of the trading cycle"""
<<<<<<< HEAD
        print(f"\n📊 SDK TRADING CYCLE SUMMARY - {results.get('timestamp', 'Unknown')}")
=======
        print(f"\n📊 TRADING CYCLE SUMMARY - {results.get('timestamp', 'Unknown')}")
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2
        print("-" * 60)
        
        if not results.get('market_open', False):
            print("🏪 Market is CLOSED - No trading activity")
            return
        
<<<<<<< HEAD
        cycle_type = results.get('cycle_type', 'trading')
        print(f"🔄 Cycle Type: {cycle_type.upper()}")
        
        successful_agents = 0
        failed_agents = 0
        
        for agent_name, agent_results in results.get('agents', {}).items():
            status = agent_results.get('status', 'unknown')
            if status == 'completed':
                successful_agents += 1
                performance = agent_results.get('performance', {})
                total_trades = performance.get('total_trades', 0)
                print(f"👤 {agent_name}: ✅ Completed ({total_trades} total trades)")
            elif status == 'failed':
                failed_agents += 1
                error = agent_results.get('error', 'Unknown error')
                print(f"👤 {agent_name}: ❌ Failed - {error}")
            else:
                print(f"👤 {agent_name}: ❓ Status unknown")
        
        print(f"\n📈 Agents completed successfully: {successful_agents}/{len(results.get('agents', {}))}")
        if failed_agents > 0:
            print(f"❌ Agents failed: {failed_agents}")
        print(f"⏱️  Cycle duration: {results.get('duration_seconds', 0):.1f} seconds")
        print("-" * 60)
    
    async def run_continuous(self, cycle_interval_minutes: int = 60):
=======
        total_trades = 0
        for agent_name, agent_results in results.get('agents', {}).items():
            if 'decisions' in agent_results:
                decisions = agent_results['decisions']
                trades = [d for d in decisions if d['action'] != 'hold']
                total_trades += len(trades)
                
                print(f"👤 {agent_name}:")
                if trades:
                    for trade in trades:
                        action_emoji = "🟢" if trade['action'] == 'buy' else "🔴"
                        print(f"   {action_emoji} {trade['action'].upper()} {trade['quantity']} {trade['symbol']} @ ${trade['price']:.2f}")
                        print(f"      💭 {trade['reasoning'][:100]}...")
                        print(f"      🎯 Confidence: {trade['confidence']:.1%}")
                else:
                    print("   ⏸️  HOLD - No trades executed")
                print()
        
        print(f"📈 Total trades executed: {total_trades}")
        print(f"⏱️  Cycle duration: {results.get('duration_seconds', 0):.1f} seconds")
        print("-" * 60)
    
    async def run_continuous(self):
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2
        """Run the trading system continuously"""
        if not self.agents_initialized:
            await self.initialize_system()
        
<<<<<<< HEAD
        logger.info(f"🔄 Starting continuous trading (every {cycle_interval_minutes} minutes)...")
        
        do_trade = True  # Alternate between trading and rebalancing
        
        while True:
            try:
                await self.run_single_cycle(do_trade=do_trade)
                do_trade = not do_trade  # Alternate between trading and rebalancing
                
                # Wait for next cycle
                await asyncio.sleep(cycle_interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("🛑 Continuous trading stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in continuous trading: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
=======
        logger.info("🔄 Starting continuous trading...")
        await self.orchestrator.run_continuous()
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        if not self.agents_initialized:
            return {"status": "not_initialized"}
        
<<<<<<< HEAD
        status = {
            "status": "initialized",
            "system_type": "SDK-based with OpenAI Agents SDK",
            "total_agents": len(self.agents),
            "trading_symbols": self.trading_symbols,
            "agents": {}
        }
        
        for agent in self.agents:
            status["agents"][agent.config.name] = {
                "personality": agent.config.personality,
                "risk_tolerance": agent.config.risk_tolerance,
                "model": agent.config.model_name,
                "performance": agent.get_performance_summary()
            }
=======
        status = await self.orchestrator.get_all_agent_status()
        
        # Add system-level information
        status['system'] = {
            'trading_symbols': self.trading_symbols,
            'total_agents': len(self.orchestrator.agents),
            'cycle_interval_seconds': self.orchestrator.cycle_interval
        }
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2
        
        return status
    
    def stop(self):
        """Stop the trading system"""
<<<<<<< HEAD
        logger.info("🛑 SDK Trading system stopped")

async def main():
    """Main function for running the SDK-based trading system"""
    system = TradingSystem()
    
    try:
        print("🚀 Starting SDK-based Agentic Trading System...")
=======
        self.orchestrator.stop()
        logger.info("🛑 Trading system stopped")

async def main():
    """Main function for running the trading system"""
    system = TradingSystem()
    
    try:
        print("🚀 Starting Agentic Trading System...")
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2
        print("Press Ctrl+C to stop\n")
        
        # Initialize system
        await system.initialize_system()
        
        # Run a single cycle for demonstration
        print("Running single trading cycle for demonstration...")
<<<<<<< HEAD
        await system.run_single_cycle(do_trade=True)
=======
        await system.run_single_cycle()
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2
        
        # Get system status
        print("\n📊 Getting system status...")
        status = await system.get_system_status()
<<<<<<< HEAD
        print(f"System Status: {status['status']}")
        print(f"System Type: {status['system_type']}")
        print(f"Total Agents: {status['total_agents']}")
        
        # Uncomment the line below to run continuously
        # await system.run_continuous(cycle_interval_minutes=60)
=======
        print(json.dumps(status, indent=2, default=str))
        
        # Uncomment the line below to run continuously
        # await system.run_continuous()
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"System error: {e}")
<<<<<<< HEAD
        import traceback
        traceback.print_exc()
=======
>>>>>>> b17143b68fb4c453eebe20a29c0549607f5d3eb2
    finally:
        system.stop()

if __name__ == "__main__":
    asyncio.run(main())