#!/usr/bin/env python3

import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Any

from agent_orchestrator import AgentOrchestrator
from warren_agent import create_warren_agent
from george_agent import create_george_agent
from ray_agent import create_ray_agent
from cathie_agent import create_cathie_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingSystem:
    """
    Main trading system that orchestrates all four autonomous agents
    """
    
    def __init__(self):
        self.orchestrator = AgentOrchestrator()
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
        """Initialize the trading system with all four agents"""
        logger.info("🚀 Initializing Agentic Trading System...")
        
        # Create the four legendary traders
        warren = create_warren_agent()
        george = create_george_agent()
        ray = create_ray_agent()
        cathie = create_cathie_agent()
        
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
        
        # Print agent summary
        self.print_agent_summary()
    
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
        
        print(f"📈 Trading Universe: {', '.join(self.trading_symbols)}")
        print("="*80 + "\n")
    
    async def run_single_cycle(self) -> Dict[str, Any]:
        """Run a single trading cycle"""
        if not self.agents_initialized:
            await self.initialize_system()
        
        logger.info("🔄 Running trading cycle...")
        results = await self.orchestrator.run_single_cycle()
        
        # Print cycle summary
        self.print_cycle_summary(results)
        
        return results
    
    def print_cycle_summary(self, results: Dict[str, Any]):
        """Print a summary of the trading cycle"""
        print(f"\n📊 TRADING CYCLE SUMMARY - {results.get('timestamp', 'Unknown')}")
        print("-" * 60)
        
        if not results.get('market_open', False):
            print("🏪 Market is CLOSED - No trading activity")
            return
        
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
        """Run the trading system continuously"""
        if not self.agents_initialized:
            await self.initialize_system()
        
        logger.info("🔄 Starting continuous trading...")
        await self.orchestrator.run_continuous()
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        if not self.agents_initialized:
            return {"status": "not_initialized"}
        
        status = await self.orchestrator.get_all_agent_status()
        
        # Add system-level information
        status['system'] = {
            'trading_symbols': self.trading_symbols,
            'total_agents': len(self.orchestrator.agents),
            'cycle_interval_seconds': self.orchestrator.cycle_interval
        }
        
        return status
    
    def stop(self):
        """Stop the trading system"""
        self.orchestrator.stop()
        logger.info("🛑 Trading system stopped")

async def main():
    """Main function for running the trading system"""
    system = TradingSystem()
    
    try:
        print("🚀 Starting Agentic Trading System...")
        print("Press Ctrl+C to stop\n")
        
        # Initialize system
        await system.initialize_system()
        
        # Run a single cycle for demonstration
        print("Running single trading cycle for demonstration...")
        await system.run_single_cycle()
        
        # Get system status
        print("\n📊 Getting system status...")
        status = await system.get_system_status()
        print(json.dumps(status, indent=2, default=str))
        
        # Uncomment the line below to run continuously
        # await system.run_continuous()
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"System error: {e}")
    finally:
        system.stop()

if __name__ == "__main__":
    asyncio.run(main())