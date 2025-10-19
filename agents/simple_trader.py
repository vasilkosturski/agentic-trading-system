#!/usr/bin/env python3
"""
SimpleTrader - Refactored to use direct HTTP function tools instead of internal MCPs
Keeps external MCPs for Brave Search, Memory, and Fetch (third-party services)
"""

import asyncio
import logging
from contextlib import AsyncExitStack
from datetime import datetime
from typing import List, Dict, Any

from agents import Agent, Tool, Runner, trace
from agents.mcp import MCPServerStdio

# Import direct function tools (replaces internal MCPs)
from trading_tools import TRADING_TOOLS, get_account_report, initialize_agent
from market_tools import MARKET_TOOLS

# Import MCP params only for external services (Brave Search, Memory, Fetch)
from mcp_params import researcher_mcp_server_params

# Import run tracking
from run_tracking import start_run, end_run, mark_run_as_error

logger = logging.getLogger(__name__)

class SimpleTrader:
    """Simple trader using OpenAI Agents SDK with direct function tools"""

    def __init__(self, name: str, strategy: str, model_name: str = "gpt-4o-mini"):
        self.name = name
        self.strategy = strategy
        self.model_name = model_name
        self.do_trade = True
        self.agent = None

    async def get_researcher_tool(self, researcher_mcp_servers) -> Tool:
        """Create researcher tool from external MCP servers (Brave Search, Memory, Fetch)

        These are legitimate MCPs - we don't control Brave Search or Memory services
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
- Trading tools: buy_shares, sell_shares, get_balance, get_holdings
- Market status: get_market_status, is_market_open

You have access to end-of-day market data from Polygon.io (previous trading day close).
Use these tools to carry out research, make decisions, and execute trades.

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

        # Combine all tools: researcher (MCP-based) + direct function tools
        all_tools = [researcher_tool] + TRADING_TOOLS + MARKET_TOOLS

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

        # Get account report (direct API call)
        account = await get_account_report(self.name)
        strategy = await self.get_strategy()

        # Prepare agent context for run tracking
        from trading_tools import get_balance, get_holdings
        balance = await get_balance(self.name)
        holdings = await get_holdings(self.name)
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
        run_id = await start_run(self.name, run_type, agent_context, market_conditions)
        if run_id is None:
            logger.warning(f"Failed to start run tracking for {self.name}, continuing without tracking")

        try:
            # Create agent with direct tools
            self.agent = await self.create_agent(researcher_mcp_servers)

            message = (
                self.get_trade_message(strategy, account)
                if self.do_trade
                else self.get_rebalance_message(strategy, account)
            )

            result = await Runner.run(self.agent, message, max_turns=30)

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

            # End run tracking (with placeholder values for now - could be enhanced)
            if run_id is not None:
                research_sources = []  # Could extract from researcher tool calls
                trade_count = 0  # Could count actual trades made
                await end_run(run_id, full_reasoning or "Agent execution completed", research_sources, summary or "Completed", trade_count)

            print(f"✅ {self.name} completed {cycle_type} cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            # Mark run as error if tracking was started
            if run_id is not None:
                await mark_run_as_error(run_id, str(e))
            raise  # Re-raise the exception

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
