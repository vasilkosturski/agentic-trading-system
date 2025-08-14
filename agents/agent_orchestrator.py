#!/usr/bin/env python3

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
import json

from base_agent import BaseAgent, AgentConfig
from mcp_connector import MCPManager

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """Orchestrates multiple trading agents"""
    
    def __init__(self):
        self.agents: List[BaseAgent] = []
        self.mcp_manager = None  # Will be initialized per agent with memory
        self.trading_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        self.running = False
        self.cycle_interval = 3600  # 60 minutes between trading cycles
        self.agent_mcp_managers = {}  # Store MCP manager for each agent
    
    def add_agent(self, agent: BaseAgent):
        """Add an agent to the orchestrator"""
        self.agents.append(agent)
        logger.info(f"Added agent: {agent.config.name}")
    
    async def initialize_agents(self):
        """Initialize all agents with MCP connections including memory"""
        logger.info("Initializing agents with memory systems...")
        
        # Configure each agent with MCP tools including memory
        for agent in self.agents:
            # Create individual MCP manager with memory for each agent
            agent_mcp_manager = MCPManager(agent_name=agent.config.name)
            self.agent_mcp_managers[agent.config.name] = agent_mcp_manager
            
            # Start MCP servers for this agent
            await agent_mcp_manager.start_all_servers()
            
            # Configure agent with MCP tools including memory
            agent.set_mcp_tools(
                agent_mcp_manager.accounts,
                agent_mcp_manager.market,
                agent_mcp_manager.push,
                agent_mcp_manager.memory  # Add memory tools
            )
            
            # Initialize agent account
            await agent.initialize_account()
            
            logger.info(f"Initialized agent {agent.config.name} with memory system")
        
        logger.info(f"Initialized {len(self.agents)} agents with persistent memory")
    
    async def run_single_cycle(self) -> Dict[str, Any]:
        """Run a single trading cycle for all agents"""
        cycle_start = datetime.now()
        logger.info(f"Starting trading cycle at {cycle_start}")
        
        # For demonstration purposes, assume market is always open
        # In production, you would check actual market hours
        market_open = True
        logger.info("Assuming market is open for demonstration")
        
        cycle_results = {
            "timestamp": cycle_start.isoformat(),
            "market_open": market_open,
            "agents": {}
        }
        
        # Run trading cycle for each agent
        for agent in self.agents:
            try:
                logger.info(f"Running cycle for agent: {agent.config.name}")
                
                # Get agent's decisions for all symbols
                decisions = await agent.run_trading_cycle(self.trading_symbols)
                
                # Get performance summary
                performance = agent.get_performance_summary()
                
                cycle_results["agents"][agent.config.name] = {
                    "decisions": [
                        {
                            "action": d.action,
                            "symbol": d.symbol,
                            "quantity": d.quantity,
                            "reasoning": d.reasoning,
                            "confidence": d.confidence,
                            "price": d.current_price
                        }
                        for d in decisions
                    ],
                    "performance": performance
                }
                
            except Exception as e:
                logger.error(f"Error in agent {agent.config.name}: {e}")
                cycle_results["agents"][agent.config.name] = {
                    "error": str(e)
                }
        
        cycle_end = datetime.now()
        cycle_duration = (cycle_end - cycle_start).total_seconds()
        cycle_results["duration_seconds"] = cycle_duration
        
        logger.info(f"Trading cycle completed in {cycle_duration:.2f} seconds")
        return cycle_results
    
    async def run_continuous(self):
        """Run continuous trading cycles"""
        self.running = True
        logger.info("Starting continuous trading...")
        
        try:
            await self.initialize_agents()
            
            while self.running:
                try:
                    # Run trading cycle
                    cycle_results = await self.run_single_cycle()
                    
                    # Log summary
                    self.log_cycle_summary(cycle_results)
                    
                    # Wait for next cycle
                    if self.running:
                        logger.info(f"Waiting {self.cycle_interval} seconds until next cycle...")
                        await asyncio.sleep(self.cycle_interval)
                    
                except Exception as e:
                    logger.error(f"Error in trading cycle: {e}")
                    await asyncio.sleep(60)  # Wait 1 minute before retrying
                    
        finally:
            # Stop all agent MCP managers
            for agent_name, mcp_manager in self.agent_mcp_managers.items():
                try:
                    await mcp_manager.stop_all_servers()
                    logger.info(f"Stopped MCP servers for agent {agent_name}")
                except Exception as e:
                    logger.error(f"Error stopping MCP servers for {agent_name}: {e}")
    
    def log_cycle_summary(self, cycle_results: Dict[str, Any]):
        """Log a summary of the trading cycle"""
        if cycle_results.get("market_open", False):
            total_actions = 0
            for agent_name, agent_results in cycle_results.get("agents", {}).items():
                if "decisions" in agent_results:
                    actions = [d["action"] for d in agent_results["decisions"] if d["action"] != "hold"]
                    total_actions += len(actions)
                    if actions:
                        logger.info(f"Agent {agent_name}: {len(actions)} trades executed")
            
            logger.info(f"Cycle summary: {total_actions} total trades across all agents")
        else:
            logger.info("Market closed - no trading activity")
    
    async def get_all_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "total_agents": len(self.agents),
            "agents": {}
        }
        
        for agent in self.agents:
            try:
                balance = await agent.get_account_balance()
                portfolio_value = await agent.get_portfolio_value()
                holdings = await agent.get_holdings()
                performance = agent.get_performance_summary()
                
                status["agents"][agent.config.name] = {
                    "config": {
                        "personality": agent.config.personality,
                        "risk_tolerance": agent.config.risk_tolerance,
                        "initial_balance": agent.config.initial_balance
                    },
                    "current_status": {
                        "cash_balance": balance,
                        "portfolio_value": portfolio_value,
                        "holdings": holdings
                    },
                    "performance": performance
                }
                
            except Exception as e:
                status["agents"][agent.config.name] = {
                    "error": str(e)
                }
        
        return status
    
    def stop(self):
        """Stop the orchestrator"""
        self.running = False
        logger.info("Stopping agent orchestrator...")

# Example usage and testing
async def main():
    """Main function for testing"""
    orchestrator = AgentOrchestrator()
    
    # We'll add the actual agent implementations in the next step
    # For now, this is the framework
    
    try:
        # Run a single cycle for testing
        await orchestrator.initialize_agents()
        
        if orchestrator.agents:
            results = await orchestrator.run_single_cycle()
            print(json.dumps(results, indent=2))
        else:
            print("No agents configured")
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        # Stop all agent MCP managers
        for mcp_manager in orchestrator.agent_mcp_managers.values():
            await mcp_manager.stop_all_servers()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())