#!/usr/bin/env python3
"""
SimpleTrader - Refactored to use direct HTTP function tools instead of internal MCPs
Keeps external MCPs for Brave Search and Fetch (third-party services)
Memory stored directly in PostgreSQL via trading_tools.py fields (full_reasoning, research_sources, agent_context)
"""

import asyncio
import json
import logging
from contextlib import AsyncExitStack
from datetime import datetime
from typing import List, Dict, Any, Optional

import aiohttp

from agents import Agent, Tool, Runner, trace
from agents.mcp import MCPServerStdio

# Import direct function tools (replaces internal MCPs)
from trading_tools import get_account_report, initialize_agent
from trading_tools import buy_shares, sell_shares, _get_balance_raw, _get_holdings_raw
from agents import function_tool
from market_tools import MARKET_TOOLS
from memory_tools import get_trading_history, get_recent_activity

# Import MCP params only for external services (Brave Search, Memory, Fetch)
from mcp_params import researcher_mcp_server_params

# Import run tracking
from run_tracking import start_run, end_run, mark_run_as_error

# Import status broadcasting
from status_broadcaster import broadcast_status, PHASE_INITIALIZING, PHASE_RESEARCHING, PHASE_DECIDING, PHASE_TRADING, PHASE_COMPLETED, PHASE_ERROR

# Import tool tracking
from tool_tracking import ToolTracker

logger = logging.getLogger(__name__)

class SimpleTrader:
    """Simple trader using OpenAI Agents SDK with direct function tools"""

    def __init__(self, name: str, strategy: str, model_name: str = "gpt-4o-mini", agent_id: Optional[int] = None):
        self.name = name
        self.strategy = strategy
        self.model_name = model_name
        self.do_trade = True
        self.agent = None
        # Per-run state (no globals)
        self.current_run_id: Optional[int] = None
        self.trade_count: int = 0
        self.last_decision: Optional[dict] = None
        self.agent_id: Optional[int] = agent_id  # Set at TradingSystem initialization
        self.tracker: Optional[ToolTracker] = None  # Tool tracking for transparency

    async def get_researcher_tool(self, researcher_mcp_servers) -> Tool:
        """Create researcher tool from external MCP servers (Brave Search, Fetch)

        These are legitimate MCPs - we don't control Brave Search services
        Memory is now stored directly in PostgreSQL via trading_tools.py fields
        """
        researcher_instructions = f"""You are a financial researcher. You help with research and analysis for trading decisions.
Based on the request, you carry out necessary research and respond with your findings.

Available tools:
- Brave Search: Search the web for news, information, and analysis
- Web fetch tool: Can retrieve content from specific URLs
- Knowledge graph: Store and recall information about companies, websites, and market conditions

Important: making use of your knowledge graph to retrieve and store information on companies, websites and market conditions:

Make use of your knowledge graph tools to store and recall entity information; use it to retrieve information that
you have worked on previously, and store new information about companies, stocks and market conditions.
Also use it to store web addresses that you find interesting so you can check them later.
Draw on your knowledge graph to build your expertise over time.

Focus on finding relevant news, market conditions, and company information to support trading decisions.
The current datetime is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

        researcher = Agent(
            name="Researcher",
            instructions=researcher_instructions,
            model=self.model_name,
            mcp_servers=researcher_mcp_servers,  # External MCPs - OK to use!
        )

        return researcher.as_tool(
            tool_name="Researcher",
            tool_description="This tool researches online for news and opportunities, either based on your specific request to look into a certain stock, or generally for notable financial news and opportunities. Describe what kind of research you're looking for."
        )

    def get_trader_instructions(self) -> str:
        """Get trader instructions"""
        return f"""
You are {self.name}, a trader on the stock market. Your account is under your name, {self.name}.
You actively manage your portfolio according to your strategy.

Available tools:
- Researcher: Research online for news and opportunities
- Market data tools: lookup_share_price, get_historical_prices, get_market_indicators
- Memory tools: query_trading_history(symbol, days), query_recent_activity(days)
  - Use these to remember your past decisions and reasoning about stocks
  - Check your history before making decisions to maintain consistency
- Decision tool: decide_action(action=BUY|SELL|HOLD, symbol?, quantity?, rationale, fullReasoning?)
  - rationale: Brief summary (1-2 sentences) of the trade decision
  - fullReasoning: Comprehensive analysis explaining your research, market conditions, and investment thesis (2-5 paragraphs)
- Market status: get_market_status, is_market_open

You have access to end-of-day market data from Polygon.io (previous trading day close).
Account snapshot is provided in the prompt; do not query balance/holdings via tools.

IMPORTANT: Maximum 10 positions per agent. You must sell before buying new positions if at limit.

Your goal is to maximize your profits according to your strategy.

Your investment strategy:
{self.strategy}
"""

    def get_trade_message(self, strategy: str, account: str) -> str:
        """Get trading message with updated instructions"""
        return f"""You are conducting your regular portfolio review and market analysis.

IMPORTANT: This is a REVIEW cycle, not a mandate to trade. Most of the time, you should do NOTHING.
Quality over quantity - only trade when you have strong conviction.

YOUR REVIEW PROCESS:
1. Use the research tool to check relevant news and market conditions
2. Review your current holdings - are any positions underperforming or breaking your thesis?
3. Look for potential new opportunities consistent with your strategy
4. Make a thoughtful decision: Should you sell something? Buy something? Or hold steady?

TRADING DISCIPLINE:
- **AIM FOR ~1 TRADE PER DAY MAXIMUM** - Be selective, not hyperactive
- **SELLING is just as important as BUYING**:
  - Sell positions that have broken your investment thesis
  - Take profits on winners that have reached targets
  - Cut losses on underperformers
  - Sell to make room for higher-conviction opportunities
- **BUYING should be rare and high-conviction**:
  - Only buy when you see exceptional value or opportunity
  - Ask yourself: "Is this truly better than what I already own?"
  - Prefer holding cash over mediocre investments
- **DOING NOTHING is often the best decision**:
  - If your portfolio looks good and no urgent opportunities exist, just hold
  - Don't trade for the sake of trading
  - Patience is a virtue in investing

CRITICAL - DECISION RULES:
  - At the end of your analysis, call decide_action exactly once.
  - If you decide BUY or SELL, include symbol and positive integer quantity.
  - Provide a brief rationale (1-2 sentences) and a comprehensive fullReasoning (2-5 paragraphs) explaining:
    * Your research findings and data sources
    * Market conditions and context
    * Why this aligns with your investment strategy
    * Risk considerations and position sizing rationale
  - If you decide HOLD, set action=HOLD and omit symbol/quantity.
  - The system will execute the action you decide; do NOT call any trading tools directly.

PORTFOLIO CONSTRAINTS:
- **MAXIMUM 10 POSITIONS AT ANY TIME** - This is a hard limit enforced by the system
- If you try to buy a new stock when you already hold 10 positions, you must sell one first
- Adding to existing positions (buying more shares) does NOT count toward this limit
- This forces conviction - only hold your highest-confidence ideas

Your investment strategy:
{strategy}

Here is your current account:
{account}

Here is the current datetime:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Now, conduct your review, make your decision (which may be to do nothing), and execute any trades if warranted. Your account name is {self.name}.
After your review, respond with a brief 2-3 sentence appraisal of your portfolio and its outlook.
"""

    def get_rebalance_message(self, strategy: str, account: str) -> str:
        """Get rebalancing message"""
        return f"""You are conducting a portfolio rebalancing review.

IMPORTANT: This is a REVIEW, not a mandate to rebalance. Most of the time, your portfolio is fine as-is.
Only rebalance if positions have materially drifted from your strategy or if conviction has changed.

YOUR REBALANCING REVIEW:
1. Use the research tool to check news affecting your current holdings
2. Evaluate each position: Does it still fit your strategy and risk tolerance?
3. Check if any positions have grown too large or too small relative to conviction
4. Decide if any adjustments are needed, or if portfolio should remain unchanged

REBALANCING DISCIPLINE:
- **MOST CYCLES: DO NOTHING** - If positions are working, let them work
- **SELLING criteria**:
  - Position has broken your investment thesis
  - Risk/reward no longer favorable
  - Position size has grown beyond your risk tolerance
  - Better opportunity exists and you need room (10-position limit)
- **BUYING during rebalance**:
  - Only to replace sold positions or fill gaps in strategy
  - Not about finding new opportunities (that's for trading cycles)
  - Focus on strengthening existing strategy execution

PORTFOLIO CONSTRAINTS:
- **MAXIMUM 10 POSITIONS AT ANY TIME** - Hard limit enforced by system
- If adding new position during rebalance and at 10 positions, must sell one first
- Adding to existing positions does NOT count toward limit

Your investment strategy:
{strategy}

Here is your current account:
{account}

Here is the current datetime:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Now, conduct your rebalancing review and make your decision (which may be to do nothing). Your account name is {self.name}.
After your review, respond with a brief 2-3 sentence appraisal of your portfolio and its outlook.
"""

    async def get_strategy(self) -> str:
        """Get strategy - uses hardcoded constructor strategy"""
        return self.strategy

    async def create_agent(self, researcher_mcp_servers) -> Agent:
        """Create the agent with direct function tools + researcher MCP"""
        researcher_tool = await self.get_researcher_tool(researcher_mcp_servers)

        # Add a per-agent decide_action tool that records to instance state
        @function_tool
        async def decide_action(action: str, symbol: str = None, quantity: int = None, rationale: str = None, fullReasoning: str = None) -> str:
            act = (action or "").upper()
            if act in ("BUY", "SELL"):
                if not symbol or not isinstance(quantity, int) or quantity <= 0:
                    raise ValueError("symbol and positive quantity are required for BUY/SELL")
            else:
                act = "HOLD"
                symbol = symbol or ""
                quantity = quantity or 0
            decision = {
                "action": act,
                "symbol": symbol,
                "quantity": quantity,
                "rationale": rationale or "",
                "fullReasoning": fullReasoning or "",
            }
            self.last_decision = decision
            # Return a simple acknowledgement; the system reads self.last_decision
            return "OK"

        # Memory tools - query past decisions and reasoning
        # Just use the regular memory functions - we'll track Researcher tool calls via logs
        @function_tool
        async def query_trading_history(symbol: str, days: int = 30) -> str:
            """
            Get your complete trading history for a specific stock.
            Shows all trades (BUY/SELL), your reasoning at the time, market conditions,
            and times you considered but didn't trade.
            
            Use this to remember your thesis and conviction level for a stock.
            
            Args:
                symbol: Stock symbol (e.g., 'NVDA', 'AAPL')
                days: How many days back to look (default 30)
            
            Returns:
                Natural language summary of your trading history for this stock
            """
            return await get_trading_history(self.name, symbol, days)
        
        @function_tool
        async def query_recent_activity(days: int = 7) -> str:
            """
            Get your recent trading activity across all stocks.
            Shows what you've been doing, thinking, and considering in recent runs.
            
            Use this to understand your current portfolio strategy and avoid repetitive trades.
            
            Args:
                days: How many days back to look (default 7)
            
            Returns:
                Natural language summary of your recent activity
            """
            return await get_recent_activity(self.name, days)

        # Use tools as-is - no wrapping needed
        # OpenAI SDK logs will show us when they're called
        all_tools = [researcher_tool] + MARKET_TOOLS + [decide_action, query_trading_history, query_recent_activity]

        agent = Agent(
            name=self.name,
            instructions=self.get_trader_instructions(),
            model=self.model_name,
            tools=all_tools,  # Direct function tools - no internal MCPs!
        )

        return agent

    async def run_agent(self, researcher_mcp_servers):
        """Run the agent - simplified without internal MCPs"""
        cycle_type = "trading" if self.do_trade else "rebalancing"
        run_type = "TRADING" if self.do_trade else "REBALANCE"
        print(f"🤖 {self.name} starting {cycle_type} cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Initialize agent account (direct function call, not through agent)
        await initialize_agent(self.name)

        if self.agent_id is None:
            raise RuntimeError(f"Agent id not set for {self.name}. Use TradingSystem.create() to instantiate.")
        
        # Broadcast: INITIALIZING
        broadcast_status(self.agent_id, self.name, PHASE_INITIALIZING, "Starting trading cycle", 0)
        
        # Get account report (direct API call)
        account = await get_account_report(self.agent_id)
        strategy = await self.get_strategy()

        # Prepare agent context for run tracking
        balance = await _get_balance_raw(self.agent_id)
        holdings = await _get_holdings_raw(self.agent_id)
        agent_context = {
            "balance": balance,
            "holdings": holdings,
            "positionCount": len(holdings),
        }

        # Market conditions (simplified - could be enhanced)
        market_conditions = {
            "timestamp": datetime.now().isoformat(),
            "cycle_type": cycle_type,
        }

        # Start run tracking
        run_id = await start_run(self.agent_id, self.name, run_type, agent_context, market_conditions)
        if run_id is None:
            logger.warning(f"Failed to start run tracking for {self.name}, continuing without tracking")
        else:
            self.current_run_id = run_id
            self.trade_count = 0
            self.last_decision = None
            
        # Initialize tool tracker for transparency
        self.tracker = ToolTracker(run_id)
        
        # Log initialization
        init_text = f"Starting {cycle_type} cycle. Balance: ${balance:.2f}, Positions: {len(holdings)}"
        self.tracker.log_reasoning("initialization", f"Started {cycle_type} cycle", init_text)

        try:
            # Broadcast: RESEARCHING (combined: fetching data, research, analysis)
            broadcast_status(self.agent_id, self.name, PHASE_RESEARCHING, "Researching and analyzing market opportunities", 30)
            
            # Log research phase
            self.tracker.log_reasoning("research", "Starting research", "Beginning market research and analysis")
            
            # Create agent with direct tools
            self.agent = await self.create_agent(researcher_mcp_servers)

            message = (
                self.get_trade_message(strategy, account)
                if self.do_trade
                else self.get_rebalance_message(strategy, account)
            )
            
            result = await Runner.run(self.agent, message, max_turns=30)
            
            # Broadcast: DECIDING (after agent completes reasoning)
            broadcast_status(self.agent_id, self.name, PHASE_DECIDING, "Making investment decision", 70)

            # Extract result data for run tracking
            # The result contains messages with the agent's reasoning and final response
            full_reasoning = ""
            summary = ""
            if result and hasattr(result, 'messages'):
                # Get last assistant message as summary
                assistant_messages = [m for m in result.messages if hasattr(m, 'role') and m.role == 'assistant']
                if assistant_messages:
                    last_message = assistant_messages[-1]
                    summary = last_message.content if hasattr(last_message, 'content') else str(last_message)
                    # Full reasoning is all assistant messages concatenated
                    full_reasoning = "\n\n".join(
                        m.content if hasattr(m, 'content') else str(m)
                        for m in assistant_messages
                    )

            # Read structured decision from decide_action tool (if any) and dispatch deterministically
            decision = self.last_decision
            if decision and decision.get("action") in ("BUY", "SELL"):
                # Extract decision details
                action = decision["action"]
                symbol = decision["symbol"]
                quantity = int(decision["quantity"])
                rationale = decision.get("rationale") or summary or "Decision"
                
                # Log decision
                decision_text = f"{action} {quantity} shares of {symbol}. Rationale: {rationale}"
                self.tracker.log_reasoning("decision", f"Decided: {action} {symbol}", decision_text)
                
                # Broadcast: TRADING
                broadcast_status(self.agent_id, self.name, PHASE_TRADING, "Executing trade", 90)
                # Use fullReasoning from decision if available, otherwise fall back to conversation messages
                decision_full_reasoning = decision.get("fullReasoning") or ""
                final_full_reasoning = decision_full_reasoning if decision_full_reasoning else full_reasoning
                
                # Prepare research sources as JSON
                research_sources_json = json.dumps([])  # Could be enhanced to extract from researcher tool
                
                # Prepare agent context before trade
                portfolio_context = {
                    "cashBefore": balance,
                    "positionsBefore": len(holdings),
                    "holdingsBefore": holdings,
                    "timestamp": datetime.now().isoformat(),
                }
                agent_context_json = json.dumps(portfolio_context)
                
                try:
                    if action == "BUY":
                        await buy_shares(
                            self.agent_id, 
                            symbol, 
                            quantity, 
                            rationale, 
                            fullReasoning=final_full_reasoning,
                            researchSources=research_sources_json,
                            agentContext=agent_context_json,
                            runId=self.current_run_id, 
                            agent_name=self.name
                        )
                    else:
                        await sell_shares(
                            self.agent_id, 
                            symbol, 
                            quantity, 
                            rationale, 
                            fullReasoning=final_full_reasoning,
                            researchSources=research_sources_json,
                            agentContext=agent_context_json,
                            runId=self.current_run_id, 
                            agent_name=self.name
                        )
                    self.trade_count += 1
                    
                    # Log execution success
                    self.tracker.log_reasoning("execution", f"Executed {action}", f"Successfully executed {action} {quantity} {symbol}")
                except Exception as trade_err:
                    logger.error(f"Trade execution failed: {trade_err}")
                    
                    # Log execution failure
                    self.tracker.log_reasoning("execution", f"Failed {action}", f"Trade failed: {str(trade_err)}")
            else:
                # HOLD decision
                self.tracker.log_reasoning("decision", "Decided: HOLD", f"No trades. {summary[:200] if summary else 'Portfolio unchanged'}")

            # End run tracking
            if run_id is not None:
                research_sources = []  # Could extract from researcher tool calls
                await end_run(run_id, full_reasoning or "Agent execution completed", research_sources, summary or "Completed", self.trade_count)

            # Broadcast: COMPLETED
            outcome_message = f"Completed - {self.trade_count} trade(s) executed" if self.trade_count > 0 else "Completed - No trades (HOLD decision)"
            broadcast_status(self.agent_id, self.name, PHASE_COMPLETED, outcome_message, 100, outcome=outcome_message)
            
            print(f"✅ {self.name} completed {cycle_type} cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            # Broadcast: ERROR
            broadcast_status(self.agent_id, self.name, PHASE_ERROR, f"Error: {str(e)}", 0, outcome=f"Failed: {str(e)}")
            
            # Mark run as error if tracking was started
            if run_id is not None:
                await mark_run_as_error(run_id, str(e))
            raise  # Re-raise the exception
        finally:
            self.current_run_id = None
            self.trade_count = 0
            self.last_decision = None
            self.tracker = None  # Clean up tracker

    async def run_with_mcp_servers(self):
        """Run agent with MCP server context - only for external services (Brave Search, Memory, Fetch)"""
        # Only create MCP servers for external services
        async with AsyncExitStack() as stack:
            researcher_mcp_servers = [
                await stack.enter_async_context(
                    MCPServerStdio(params, client_session_timeout_seconds=120)
                )
                for params in researcher_mcp_server_params(self.name.lower())
            ]

            await self.run_agent(researcher_mcp_servers)

    async def run_with_trace(self):
        """Run agent with tracing"""
        trace_name = f"{self.name}-trading" if self.do_trade else f"{self.name}-rebalancing"
        trace_id = f"trace_{self.name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        with trace(trace_name, trace_id=trace_id):
            await self.run_with_mcp_servers()

    async def run(self):
        """Main run method"""
        try:
            logger.info(f"Starting {self.name} agent...")
            await self.run_with_trace()
            logger.info(f"{self.name} agent completed successfully")
        except Exception as e:
            logger.error(f"Error running {self.name} agent: {e}")
        # Toggle between trading and rebalancing
        self.do_trade = not self.do_trade
