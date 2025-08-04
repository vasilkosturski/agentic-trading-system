#!/usr/bin/env python3

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
import subprocess
import sys
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MCPServerConfig:
    """Configuration for MCP server connection"""
    name: str
    script_path: str
    description: str

class MCPToolConnector:
    """Connector to interact with MCP servers via stdio"""
    
    def __init__(self, server_config: MCPServerConfig):
        self.config = server_config
        self.process = None
        self.request_id = 0
    
    async def start_server(self):
        """Start the MCP server process"""
        try:
            self.process = await asyncio.create_subprocess_exec(
                sys.executable, self.config.script_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            logger.info(f"Started MCP server: {self.config.name}")
        except Exception as e:
            logger.error(f"Failed to start MCP server {self.config.name}: {e}")
            raise
    
    async def stop_server(self):
        """Stop the MCP server process"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            logger.info(f"Stopped MCP server: {self.config.name}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server"""
        if not self.process:
            await self.start_server()
        
        self.request_id += 1
        
        # Prepare the JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            # Send request
            request_json = json.dumps(request) + '\n'
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()
            
            # Read response
            response_line = await self.process.stdout.readline()
            response = json.loads(response_line.decode().strip())
            
            if "error" in response:
                raise Exception(f"MCP tool error: {response['error']}")
            
            return response.get("result", {}).get("content", [{}])[0].get("text")
            
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            raise

class AccountsToolConnector(MCPToolConnector):
    """Connector for accounts MCP server tools"""
    
    def __init__(self):
        super().__init__(MCPServerConfig(
            name="accounts_server",
            script_path="mcp-servers/accounts_server.py",
            description="Account management tools"
        ))
    
    async def get_balance(self, account_id: str) -> Dict[str, Any]:
        """Get account balance"""
        result = await self.call_tool("get_balance", {"account_id": account_id})
        return json.loads(result)
    
    async def buy_shares(self, account_id: str, symbol: str, quantity: int) -> Dict[str, Any]:
        """Buy shares"""
        result = await self.call_tool("buy_shares", {
            "account_id": account_id,
            "symbol": symbol,
            "quantity": quantity
        })
        return json.loads(result)
    
    async def sell_shares(self, account_id: str, symbol: str, quantity: int) -> Dict[str, Any]:
        """Sell shares"""
        result = await self.call_tool("sell_shares", {
            "account_id": account_id,
            "symbol": symbol,
            "quantity": quantity
        })
        return json.loads(result)
    
    async def get_holdings(self, account_id: str) -> Dict[str, Any]:
        """Get account holdings"""
        result = await self.call_tool("get_holdings", {"account_id": account_id})
        return json.loads(result)
    
    async def change_strategy(self, account_id: str, strategy: str) -> str:
        """Change trading strategy"""
        return await self.call_tool("change_strategy", {
            "account_id": account_id,
            "strategy": strategy
        })
    
    async def create_account(self, name: str, initial_balance: float, strategy: str) -> str:
        """Create a new account (simplified - calls backend directly)"""
        # For now, we'll use a simple approach and return a generated account ID
        # In a real implementation, this would call the backend API
        import uuid
        account_id = f"agent_{name.lower().replace(' ', '_')}_{str(uuid.uuid4())[:8]}"
        logger.info(f"Created account {account_id} for {name}")
        return account_id

class MarketToolConnector(MCPToolConnector):
    """Connector for market MCP server tools"""
    
    def __init__(self):
        super().__init__(MCPServerConfig(
            name="market_server",
            script_path="mcp-servers/market_server.py",
            description="Market data tools"
        ))
    
    async def lookup_share_price(self, symbol: str) -> float:
        """Get current share price"""
        result = await self.call_tool("lookup_share_price", {"symbol": symbol})
        return float(result)
    
    async def get_historical_prices(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get historical prices"""
        result = await self.call_tool("get_historical_prices", {
            "symbol": symbol,
            "days": days
        })
        return json.loads(result)
    
    async def get_market_indicators(self, symbol: str) -> Dict[str, float]:
        """Get market indicators"""
        result = await self.call_tool("get_market_indicators", {"symbol": symbol})
        return json.loads(result)
    
    async def get_market_status(self) -> Dict[str, str]:
        """Get market status"""
        result = await self.call_tool("get_market_status", {})
        return json.loads(result)
    
    async def is_market_open(self) -> bool:
        """Check if market is open"""
        result = await self.call_tool("is_market_open", {})
        return json.loads(result)
    
    async def analyze_stock_trend(self, symbol: str, days: int = 20) -> Dict[str, Any]:
        """Analyze stock trend"""
        result = await self.call_tool("analyze_stock_trend", {
            "symbol": symbol,
            "days": days
        })
        return json.loads(result)

class PushToolConnector(MCPToolConnector):
    """Connector for push notification MCP server tools"""
    
    def __init__(self):
        super().__init__(MCPServerConfig(
            name="push_server",
            script_path="mcp-servers/push_server.py",
            description="Push notification tools"
        ))
    
    async def send_notification(self, message: str, priority: str = "normal") -> str:
        """Send push notification"""
        return await self.call_tool("send_notification", {
            "message": message,
            "priority": priority
        })

class MemoryToolConnector(MCPToolConnector):
    """Connector for LibSQL Memory MCP server tools"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        memory_db_path = f"./agents/memory/{agent_name.lower()}.db"
        
        # Ensure memory directory exists
        os.makedirs("./agents/memory", exist_ok=True)
        
        super().__init__(MCPServerConfig(
            name=f"memory_server_{agent_name}",
            script_path="npx",  # Will be handled differently for external commands
            description=f"LibSQL Memory tools for {agent_name}"
        ))
        self.memory_db_path = memory_db_path
    
    async def start_server(self):
        """Start the LibSQL Memory MCP server process"""
        try:
            env = os.environ.copy()
            env["LIBSQL_URL"] = f"file:{self.memory_db_path}"
            
            self.process = await asyncio.create_subprocess_exec(
                "npx", "-y", "mcp-memory-libsql",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            logger.info(f"Started LibSQL Memory server for {self.agent_name}")
        except Exception as e:
            logger.error(f"Failed to start LibSQL Memory server for {self.agent_name}: {e}")
            raise
    
    async def create_entities(self, entities: List[Dict[str, Any]]) -> str:
        """Create entities in the knowledge graph"""
        return await self.call_tool("create_entities", {"entities": entities})
    
    async def create_relations(self, relations: List[Dict[str, Any]]) -> str:
        """Create relations between entities"""
        # Ensure all relation fields are properly defined
        validated_relations = []
        for relation in relations:
            validated_relation = {
                "from": str(relation.get("from", "")),
                "to": str(relation.get("to", "")),
                "relationType": str(relation.get("relationType", "related_to"))
            }
            validated_relations.append(validated_relation)
        return await self.call_tool("create_relations", {"relations": validated_relations})
    
    async def add_observations(self, observations: List[Dict[str, Any]]) -> str:
        """Add observations to existing entities"""
        return await self.call_tool("add_observations", {"observations": observations})
    
    async def search_nodes(self, query: str) -> str:
        """Search for nodes in the knowledge graph"""
        return await self.call_tool("search_nodes", {"query": query})
    
    async def open_nodes(self, names: List[str]) -> str:
        """Open specific nodes by their names"""
        return await self.call_tool("open_nodes", {"names": names})
    
    async def read_graph(self) -> str:
        """Read the entire knowledge graph"""
        return await self.call_tool("read_graph", {})
    
    async def store_trading_decision(self, symbol: str, action: str, reasoning: str, price: float, quantity: int) -> str:
        """Store a trading decision in memory"""
        import time
        timestamp = int(time.time())
        entities = [{
            "name": f"trade_{symbol}_{action}_{timestamp}",
            "entityType": "trading_decision",
            "observations": [
                f"Symbol: {symbol}",
                f"Action: {action}",
                f"Price: ${price}",
                f"Quantity: {quantity}",
                f"Reasoning: {reasoning}",
                f"Agent: {self.agent_name}",
                f"Timestamp: {timestamp}"
            ]
        }]
        return await self.create_entities(entities)
    
    async def store_market_analysis(self, symbol: str, analysis: str, indicators: Dict[str, Any]) -> str:
        """Store market analysis in memory"""
        import time
        timestamp = int(time.time())
        entities = [{
            "name": f"analysis_{symbol}_{timestamp}",
            "entityType": "market_analysis",
            "observations": [
                f"Symbol: {symbol}",
                f"Analysis: {analysis}",
                f"Indicators: {json.dumps(indicators)}",
                f"Agent: {self.agent_name}",
                f"Timestamp: {timestamp}"
            ]
        }]
        return await self.create_entities(entities)
    
    async def retrieve_past_decisions(self, symbol: str = None) -> str:
        """Retrieve past trading decisions"""
        if symbol:
            query = f"trading_decision {symbol}"
        else:
            query = "trading_decision"
        
        # Try search first, if no results, try reading entire graph
        result = await self.search_nodes(query)
        if not result or result == '{"entities": [], "relations": []}':
            # Fallback to reading entire graph and filtering
            graph = await self.read_graph()
            return graph
        return result
    
    async def retrieve_market_insights(self, symbol: str = None) -> str:
        """Retrieve past market analysis"""
        if symbol:
            query = f"market_analysis {symbol}"
        else:
            query = "market_analysis"
        
        # Try search first, if no results, try reading entire graph
        result = await self.search_nodes(query)
        if not result or result == '{"entities": [], "relations": []}':
            # Fallback to reading entire graph and filtering
            graph = await self.read_graph()
            return graph
        return result

class MCPManager:
    """Manager for all MCP tool connections"""
    
    def __init__(self, agent_name: str = None):
        self.accounts = AccountsToolConnector()
        self.market = MarketToolConnector()
        self.push = PushToolConnector()
        self.memory = MemoryToolConnector(agent_name) if agent_name else None
        
        self.servers = [self.accounts, self.market, self.push]
        if self.memory:
            self.servers.append(self.memory)
    
    async def start_all_servers(self):
        """Start all MCP servers"""
        for server in self.servers:
            try:
                await server.start_server()
            except Exception as e:
                logger.error(f"Failed to start server {server.config.name}: {e}")
    
    async def stop_all_servers(self):
        """Stop all MCP servers"""
        for server in self.servers:
            try:
                await server.stop_server()
            except Exception as e:
                logger.error(f"Failed to stop server {server.config.name}: {e}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_all_servers()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop_all_servers()