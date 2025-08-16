#!/usr/bin/env python3

import asyncio
import logging
import sys
import os
from datetime import datetime
import json

# Add agents directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'agents'))

from trading_system import TradingSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agent_activity.log')
    ]
)
logger = logging.getLogger(__name__)

class AgentActivator:
    """
    Activates the 4 autonomous trading agents and runs them in active trading mode
    """
    
    def __init__(self):
        self.trading_system = TradingSystem()
        self.running = False
    
    async def activate_agents(self):
        """Activate all 4 trading agents"""
        logger.info("🚀 PHASE 5.1: Activating Autonomous Trading Agents")
        logger.info("=" * 60)
        
        try:
            # Initialize the trading system
            await self.trading_system.initialize_system()
            
            # Verify agents are initialized
            status = await self.trading_system.get_system_status()
            logger.info(f"✅ System initialized with {status['system']['total_agents']} agents")
            
            # Print initial agent status
            self.print_agent_status(status)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to activate agents: {e}")
            return False
    
    def print_agent_status(self, status):
        """Print current status of all agents"""
        print("\n📊 INITIAL AGENT STATUS")
        print("-" * 50)
        
        for agent_name, agent_data in status.get('agents', {}).items():
            if 'error' in agent_data:
                print(f"❌ {agent_name}: ERROR - {agent_data['error']}")
            else:
                current = agent_data.get('current_status', {})
                config = agent_data.get('config', {})
                
                print(f"👤 {agent_name} ({config.get('personality', 'Unknown')})")
                print(f"   💰 Cash Balance: ${current.get('cash_balance', 0):,.2f}")
                print(f"   📈 Portfolio Value: ${current.get('portfolio_value', 0):,.2f}")
                print(f"   📊 Holdings: {len(current.get('holdings', {}))}")
                print(f"   ⚡ Risk Level: {config.get('risk_tolerance', 'Unknown')}")
                print()
    
    async def run_single_trading_cycle(self):
        """Run a single trading cycle to generate activity"""
        logger.info("🔄 Running Single Trading Cycle...")
        
        try:
            # Run trading cycle
            results = await self.trading_system.run_single_cycle()
            
            # Log results
            self.log_trading_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Trading cycle failed: {e}")
            return None
    
    def log_trading_results(self, results):
        """Log the results of a trading cycle"""
        if not results:
            return
        
        print(f"\n📈 TRADING CYCLE RESULTS - {results.get('timestamp')}")
        print("-" * 60)
        
        if not results.get('market_open', False):
            print("🏪 Market is CLOSED - No trading activity")
            return
        
        total_trades = 0
        total_value_traded = 0
        
        for agent_name, agent_results in results.get('agents', {}).items():
            if 'error' in agent_results:
                print(f"❌ {agent_name}: ERROR - {agent_results['error']}")
                continue
            
            decisions = agent_results.get('decisions', [])
            trades = [d for d in decisions if d.get('action') != 'hold']
            total_trades += len(trades)
            
            print(f"\n👤 {agent_name}:")
            if trades:
                for trade in trades:
                    action_emoji = "🟢" if trade['action'] == 'buy' else "🔴"
                    trade_value = trade['quantity'] * trade['price']
                    total_value_traded += trade_value
                    
                    print(f"   {action_emoji} {trade['action'].upper()} {trade['quantity']} {trade['symbol']} @ ${trade['price']:.2f}")
                    print(f"      💵 Trade Value: ${trade_value:,.2f}")
                    print(f"      💭 Reasoning: {trade['reasoning'][:80]}...")
                    print(f"      🎯 Confidence: {trade['confidence']:.1%}")
            else:
                print("   ⏸️  HOLD - No trades executed")
        
        print(f"\n📊 CYCLE SUMMARY:")
        print(f"   🔢 Total Trades: {total_trades}")
        print(f"   💰 Total Value Traded: ${total_value_traded:,.2f}")
        print(f"   ⏱️  Duration: {results.get('duration_seconds', 0):.1f} seconds")
        print("-" * 60)
    
    async def run_continuous_trading(self, cycles: int = 3):
        """Run multiple trading cycles for demonstration"""
        logger.info(f"🔄 Running {cycles} Trading Cycles...")
        
        results_summary = []
        
        for cycle in range(cycles):
            logger.info(f"\n🔄 CYCLE {cycle + 1}/{cycles}")
            
            # Run trading cycle
            results = await self.run_single_trading_cycle()
            if results:
                results_summary.append(results)
            
            # Wait between cycles (shorter for demo)
            if cycle < cycles - 1:
                logger.info("⏳ Waiting 30 seconds before next cycle...")
                await asyncio.sleep(30)
        
        # Print summary
        self.print_cycles_summary(results_summary)
        
        return results_summary
    
    def print_cycles_summary(self, results_list):
        """Print summary of multiple cycles"""
        if not results_list:
            return
        
        print(f"\n📊 MULTI-CYCLE SUMMARY ({len(results_list)} cycles)")
        print("=" * 60)
        
        total_trades = 0
        total_value = 0
        agent_activity = {}
        
        for results in results_list:
            for agent_name, agent_results in results.get('agents', {}).items():
                if 'decisions' in agent_results:
                    trades = [d for d in agent_results['decisions'] if d.get('action') != 'hold']
                    total_trades += len(trades)
                    
                    if agent_name not in agent_activity:
                        agent_activity[agent_name] = {'trades': 0, 'value': 0}
                    
                    agent_activity[agent_name]['trades'] += len(trades)
                    
                    for trade in trades:
                        trade_value = trade['quantity'] * trade['price']
                        total_value += trade_value
                        agent_activity[agent_name]['value'] += trade_value
        
        print(f"🔢 Total Trades Across All Cycles: {total_trades}")
        print(f"💰 Total Value Traded: ${total_value:,.2f}")
        print(f"\n👥 Agent Activity:")
        
        for agent_name, activity in agent_activity.items():
            print(f"   {agent_name}: {activity['trades']} trades, ${activity['value']:,.2f} value")
        
        print("=" * 60)

async def main():
    """Main function to activate agents and run trading cycles"""
    activator = AgentActivator()
    
    try:
        print("🚀 AGENTIC TRADING SYSTEM - AGENT ACTIVATION")
        print("=" * 60)
        print("Phase 5.1: Activating agents and generating real trading data")
        print("This data will flow: Agents → MCP → Java Backend → PostgreSQL")
        print("=" * 60)
        
        # Step 1: Activate agents
        success = await activator.activate_agents()
        if not success:
            logger.error("❌ Failed to activate agents")
            return
        
        # Step 2: Run trading cycles to generate data
        print("\n🎯 GENERATING TRADING ACTIVITY...")
        await activator.run_continuous_trading(cycles=3)
        
        # Step 3: Get final status
        print("\n📊 FINAL AGENT STATUS...")
        final_status = await activator.trading_system.get_system_status()
        activator.print_agent_status(final_status)
        
        print("\n✅ PHASE 5.1 COMPLETE!")
        print("🔍 Next: Check PostgreSQL database for trading records")
        print("🖥️  Then: Verify frontend displays this real data")
        
    except KeyboardInterrupt:
        logger.info("⏹️  Interrupted by user")
    except Exception as e:
        logger.error(f"❌ System error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        activator.trading_system.stop()
        logger.info("🛑 Agent activation complete")

if __name__ == "__main__":
    asyncio.run(main())