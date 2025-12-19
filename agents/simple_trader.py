#!/usr/bin/env python3
"""
SimpleTrader - Refactored to use AgentExecutor for orchestration
Keeps external MCPs for Brave Search and Fetch (third-party services)
Memory stored directly in PostgreSQL via trading_tools.py fields (full_reasoning, research_sources, agent_context)
"""

import asyncio
import json
import logging
from contextlib import AsyncExitStack
from datetime import datetime
from typing import List, Dict, Any, Optional, Literal, cast

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

# Import researcher from new centralized module
from researcher import get_researcher_tool

# Import agent executor for orchestration
from agent_executor import AgentExecutor

logger = logging.getLogger(__name__)


class MessageBuilder:
    """Builds agent messages for trading and rebalancing cycles."""

    def __init__(self, simple_trader):
        """Initialize with reference to SimpleTrader for access to methods."""
        self.trader = simple_trader

    def build_message(
        self, historical_context: str, force_trade: bool
    ) -> str:
        """Build agent message for portfolio review cycle.

        Args:
            historical_context: Pre-fetched trading history JSON (baseline context)
            force_trade: If True, agent must make BUY/SELL (no HOLD)

        Returns:
            Complete message string for agent
        """
        strategy = self.trader.strategy
        account = "Account info loaded"  # Placeholder - actual loading handled in executor

        return self.trader.get_portfolio_review_message(
            strategy, account, historical_context, force_trade
        )


class ToolFactory:
    """Creates agent tools and researcher for trading cycles."""

    def __init__(self, simple_trader, researcher_mcp_servers):
        """Initialize with reference to SimpleTrader and MCP servers."""
        self.trader = simple_trader
        self.researcher_mcp_servers = researcher_mcp_servers

    async def create_agent(self, executor: AgentExecutor) -> Agent:
        """Create agent with all tools.

        Args:
            executor: AgentExecutor instance for decision storage

        Returns:
            Agent instance ready to run
        """
        # Create researcher tool from centralized researcher module
        researcher_tool = await get_researcher_tool(
            self.researcher_mcp_servers,
            self.trader.model_name
        )

        # Create decide_action tool that stores decision in executor
        @function_tool
        async def decide_action(
            action: str,
            symbol: Optional[str] = None,
            quantity: Optional[int] = None,
            rationale: Optional[str] = None,
            fullReasoning: Optional[str] = None,
            researchSources: Optional[str] = None,
            historicalContext: Optional[str] = None,
        ) -> str:
            """Record your trading decision with research sources and historical context.

            ⚠️ CRITICAL: You MUST call Researcher before calling this function.
            """

            # ENFORCEMENT: Check if research was conducted
            if not executor.tracker or not executor.tracker.research_queries:
                raise ValueError(
                    "❌ RESEARCH REQUIRED: You must call Researcher at least once before making decisions.\n"
                    "Markets change constantly - always gather current information first.\n"
                    "Call researcher() with your portfolio context before deciding.\n\n"
                    "Example: researcher('I am Warren. Review my holdings and check for news on each position')"
                )

            act = (action or "").upper()

            # CRITICAL DEBUG: Log what agent is passing
            logger.error(f"🔴 DECIDE_ACTION CALLED: action={action}, symbol={symbol}, quantity={quantity}")
            logger.error(f"🔴 DECIDE_ACTION RATIONALE: {rationale[:200] if rationale else 'None'}")

            # VALIDATION: Check if action matches reasoning
            if act in ("BUY", "SELL"):
                if not symbol or not isinstance(quantity, int) or quantity <= 0:
                    raise ValueError("symbol and positive quantity are required for BUY/SELL")

                reasoning_text = (rationale or "") + " " + (fullReasoning or "")
                reasoning_lower = reasoning_text.lower()

                if act == "BUY" and ("sell" in reasoning_lower or "selling" in reasoning_lower):
                    rationale_excerpt = (rationale or "")[:100]
                    error_msg = f"CRITICAL ERROR: action=BUY but reasoning mentions 'sell'. Reasoning: {rationale_excerpt}"
                    logger.error(f"🚨 {error_msg}")
                    raise ValueError(error_msg)

                if act == "SELL" and ("buy" in reasoning_lower or "buying" in reasoning_lower):
                    rationale_excerpt = (rationale or "")[:100]
                    error_msg = f"CRITICAL ERROR: action=SELL but reasoning mentions 'buy'. Reasoning: {rationale_excerpt}"
                    logger.error(f"🚨 {error_msg}")
                    raise ValueError(error_msg)
            else:
                act = "HOLD"
                symbol = symbol or ""
                quantity = quantity or 0

            # Store decision in executor
            # Cast to Literal since we've validated act is BUY/SELL/HOLD above
            executor.store_decision(
                action=cast(Literal["BUY", "SELL", "HOLD"], act),
                symbol=symbol,
                quantity=quantity,
                rationale=rationale or "",
                full_reasoning=fullReasoning or "",
                research_sources=researchSources or "[]",
                historical_context=historicalContext or "[]",
            )

            return "Decision recorded. The system will validate and execute this trade."

        # Create memory query tools
        @function_tool
        async def query_trading_history(symbol: str, days: int = 30) -> str:
            """Get your complete trading history for a specific stock."""
            result = await get_trading_history(self.trader.name, symbol, days)
            # Track historical data access if tracker available
            if executor.tracker and result:
                summary = result[:150] + "..." if len(result) > 150 else result
                executor.tracker.log_data_access(f"Trading History ({symbol})", summary)
            return result

        @function_tool
        async def query_recent_activity(days: int = 7) -> str:
            """Get your recent trading activity across all stocks."""
            result = await get_recent_activity(self.trader.name, days)
            # Track historical data access if tracker available
            if executor.tracker and result:
                summary = result[:150] + "..." if len(result) > 150 else result
                executor.tracker.log_data_access(f"Recent Activity ({days}d)", summary)
            return result

        # Combine all tools
        all_tools = [
            researcher_tool,
            *MARKET_TOOLS,
            decide_action,
            query_trading_history,
            query_recent_activity,
        ]

        agent = Agent(
            name=self.trader.name,
            instructions=self.trader.get_trader_instructions(),
            model=self.trader.model_name,
            tools=all_tools,
        )

        return agent


class SimpleTrader:
    """Simple trader using OpenAI Agents SDK with AgentExecutor orchestration."""

    def __init__(self, name: str, strategy: str, model_name: str = "gpt-4o-mini", agent_id: Optional[int] = None):
        self.name = name
        self.strategy = strategy
        self.model_name = model_name
        self.agent = None
        self.agent_id: Optional[int] = agent_id  # Set at TradingSystem initialization

        # Execution is now delegated to AgentExecutor
        self.executor: Optional[AgentExecutor] = None

    def _extract_urls_from_text(self, text: str) -> List[Dict[str, str]]:
        """Extract URLs and titles from Researcher's SOURCE citations.

        Args:
            text: Text containing SOURCE citations in format [SOURCE: Title](URL)

        Returns:
            List of dicts with 'title' and 'url' keys
        """
        import re

        sources = []

        # Pattern 1: SOURCE citations (priority) - [SOURCE: Title](URL)
        source_pattern = r'\[SOURCE:\s*([^\]]+)\]\(([^)]+)\)'
        source_citations = re.findall(source_pattern, text)
        for title, url in source_citations:
            if url.startswith('http'):
                sources.append({"title": title.strip(), "url": url.strip()})

        # Pattern 2: Regular markdown links (fallback) - [Title](URL)
        if not sources:
            markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', text)
            for title, url in markdown_links:
                if url.startswith('http') and 'SOURCE' not in title:
                    sources.append({"title": title.strip(), "url": url.strip()})

        # Pattern 3: Plain URLs (last resort fallback)
        if not sources:
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            urls = re.findall(url_pattern, text)
            for url in urls[:5]:  # Limit to 5
                # Try to extract domain as title
                domain = url.split('//')[-1].split('/')[0]
                sources.append({"title": domain, "url": url})

        return sources  # Return all SOURCE citations (no arbitrary limit)

    def _parse_research_summary(self, research_text: str, sources: List[Dict[str, str]]) -> str:
        """Parse research result to create summary with source count.

        Args:
            research_text: Full research result text (with SOURCE citations)
            sources: List of extracted URL citations from agent

        Returns:
            Clean summary of research with source count
        """
        if not research_text:
            return "Research completed"

        # Remove SOURCE citation markers to get clean text
        import re
        clean_text = re.sub(r'\[SOURCE:[^\]]+\]\([^)]+\)', '', research_text)

        # Get first 250 chars of meaningful content
        lines = [line.strip() for line in clean_text.split('\n') if line.strip() and not line.strip().startswith('http')]
        summary_text = ' '.join(lines)[:250].strip()

        if len(' '.join(lines)) > 250:
            summary_text += "..."

        # Add source citation count
        if sources:
            summary_text += f" (Cited {len(sources)} source{'s' if len(sources) != 1 else ''})"

        return summary_text if summary_text else "Research completed"

    def get_trader_instructions(self) -> str:
        """Get trader instructions"""
        return f"""
⚠️ MANDATORY: You MUST call Researcher at least once per cycle before making decisions.
If you try to call decide_action without researching first, you will get an error.

You are {self.name}, a trader on the stock market. Your account is under your name, {self.name}.
You actively manage your portfolio according to your strategy.

Available tools:
- Researcher: Research online for news and opportunities (returns JSON with summary and sources)
- Market data tools: lookup_share_price, get_historical_prices, get_market_indicators
- Memory tools: query_trading_history(symbol, days), query_recent_activity(days)
  - Use these to remember your past decisions and reasoning about stocks
  - Check your history before making decisions to maintain consistency

**USING THE RESEARCHER TOOL EFFECTIVELY**:

You can (and should) call Researcher MULTIPLE TIMES per cycle for different purposes:

Example uses:
1. **Portfolio Review**: researcher("I am {self.name}. Review my current holdings and find news on each position")
2. **Opportunity Search**: researcher("I am {self.name} focusing on my strategy. Find opportunities that match my investment approach")
3. **Sector Analysis**: researcher("Analyze the financial sector outlook and identify risks")
4. **Stock Deep Dive**: researcher("I hold 150 NVDA bought at $145 for AI thesis. Research latest earnings, outlook, and competitive position")

**ENRICHING RESEARCH REQUESTS**:

Provide context about what you're looking for:

❌ Bad: researcher("research stocks")
✅ Good: researcher("I'm {self.name} focusing on my strategy. Review my holdings and find opportunities")

❌ Bad: researcher("what about NVDA")
✅ Good: researcher("I hold 150 NVDA bought at $145 for AI thesis. Check latest earnings and sentiment")

The Researcher has access to your portfolio and history - it will automatically query
your holdings and past decisions when you mention your name.

**MULTIPLE CALLS**:

Example cycle:
1. researcher("I am {self.name}. Review my holdings - any red flags?")
2. researcher("Find 2-3 new opportunities matching my investment strategy")
3. researcher("I'm considering selling AAPL. Deep dive on recent performance and outlook")

Each call is tracked and sources are saved for transparency.

**CRITICAL - Decision Workflow (YOU MUST FOLLOW ALL 3 STEPS):**

1. **Historical Context - MANDATORY FIRST STEP**:
   - **YOU MUST CALL query_trading_history(symbol, days) for ANY stock you're considering**
   - This is NOT optional - call it even if you think there's no history
   - Analyze the fullReasoning from your previous decisions
   - Extract specific insights with symbol, quantity, price, action
   - Structure as: {{"summary": "Key patterns", "insights": [{{"date": "2025-11-30", "insight": "Bought 50 NVDA at $145 - AI growth thesis"}}]}}
   - If query returns no data, THEN you can use empty insights: {{"summary": "No prior trades", "insights": []}}
   - Store this JSON - you'll pass it to decide_action as historicalContext

2. **Research**: Use the Researcher tool to gather market information
   - Researcher returns a JSON object with TWO fields: {{"summary": "...", "sources": [...]}}
   - The "sources" array contains objects like: {{"title": "Article Title", "url": "https://..."}}
   - **CRITICAL**: You MUST pass the COMPLETE JSON from Researcher to decide_action as researchSources
   - Do NOT just copy the summary - include the ENTIRE JSON with the sources array
   - Example: researchSources='{{"summary": "Market analysis...", "sources": [{{"title": "...", "url": "..."}}]}}'
   - **CITE SOURCES**: In your fullReasoning, cite key sources by title to show which facts support your decision
   - Example: "According to TechCrunch, NVIDIA's AI chip demand is surging, which supports a BUY decision."

3. **Decide**: Call decide_action() EXACTLY ONCE at the end with your decision, research sources, AND historical context

   To BUY a stock:
     # STEP 1: Query historical context FIRST
     history = query_trading_history("NVDA", 30)
     # Build JSON from history data
     historicalContext = '{{"summary": "Past NVDA trades", "insights": [{{"date": "2025-11-30", "insight": "Bought 100 NVDA at $177"}}]}}'

     # STEP 2: Get research from Researcher tool
     # (call Researcher tool here)

     # STEP 3: Decide with both research and history
     decide_action(
       action="BUY",
       symbol="NVDA",
       quantity=50,
       rationale="Brief reason",
       fullReasoning="Complete analysis",
       researchSources='{{"summary": "...", "sources": [...]}}',  # COMPLETE JSON from Researcher
       historicalContext=historicalContext  # JSON from query_trading_history above
     )

   To SELL a stock:
     # STEP 1: Query historical context FIRST (must call for ANY decision!)
     history = query_trading_history("NVDA", 30)
     # Build JSON from history
     historicalContext = '{{"summary": "...", "insights": [...]}}'

     # STEP 2 & 3: Research + Decide
     decide_action(
       action="SELL",
       symbol="NVDA",
       quantity=50,
       rationale="Brief reason",
       fullReasoning="Complete analysis",
       researchSources='{{"summary": "...", "sources": [...]}}',  # From Researcher
       historicalContext=historicalContext  # From query_trading_history
     )

   To do nothing:
     decide_action(action="HOLD", rationale="...", fullReasoning="...")

**IMPORTANT:**
- The action parameter MUST be "BUY", "SELL", or "HOLD" - nothing else
- Your rationale and fullReasoning must match your action (don't say "sell" if action="BUY")
- Always pass researchSources (the Researcher's JSON) to decide_action for transparency
- Always pass historicalContext (your analysis of past trades) to decide_action for transparency

You have access to end-of-day market data from Polygon.io (previous trading day close).
Account snapshot is provided in the prompt; do not query balance/holdings via tools.

IMPORTANT: Maximum 10 positions per agent. You must sell before buying new positions if at limit.

Your goal is to maximize your profits according to your strategy.

Your investment strategy:
{self.strategy}
"""

    def get_portfolio_review_message(self, strategy: str, account: str, historical_context: Optional[str] = None, force_trade: bool = False) -> str:
        """Get unified portfolio review message that supports proactive trading and prudent risk management.

        Args:
            strategy: Investment strategy description
            account: Account information
            historical_context: Pre-fetched trading history JSON
            force_trade: If True, agent MUST make a BUY or SELL trade (no HOLD allowed)
        """
        historical_section = ""
        if historical_context:
            historical_section = f"""
---
YOUR TRADING HISTORY (pre-fetched for you):
{historical_context}

Use this historical context to inform your decisions. Reference specific past trades when making new decisions.
---
"""

        force_trade_instruction = ""
        if force_trade:
            force_trade_instruction = """
🎯 **MANUAL TRIGGER - ACTION REQUIRED**:
This is a MANUAL trading cycle triggered by the user. You MUST make an actual trade (BUY or SELL) this cycle.
- HOLD is NOT allowed this time
- Choose your best opportunity: either BUY a new position or SELL an existing one
- If all positions look good, consider: taking profits on a winner, rebalancing, or adding to a high-conviction position
- Make a decisive trade that demonstrates your strategy

"""

        return f"""{force_trade_instruction}You are conducting your regular portfolio review and market analysis.

THIS IS A SIMULATION ENVIRONMENT - Be active and demonstrate your trading strategy!
Your goal is to build and manage an interesting portfolio that reflects your investment philosophy.

YOUR PORTFOLIO REVIEW APPROACH:
1. Use the Researcher tool to check relevant news and market conditions
   - Researcher returns JSON with summary and sources
   - Save this JSON - you'll need to pass it to decide_action for transparency
2. Review your current holdings:
   - Are any underperforming or ready to take profits?
   - Does each position still fit your strategy and risk tolerance?
   - Are position sizes aligned with your conviction levels?
3. Actively look for new opportunities consistent with your strategy
4. Make decisions to either improve your portfolio or capitalize on opportunities

BALANCED DECISION-MAKING:
- **BE PROACTIVE**: This is your chance to demonstrate your trading style
- **BUILD POSITIONS**: If you have cash and see opportunities aligned with your strategy, take action
- **MANAGE ACTIVELY**: Don't be afraid to adjust positions based on market conditions
- **SELLING is important**:
  - Sell positions that have broken your investment thesis
  - Take profits on winners that have reached targets
  - Cut losses on underperformers
  - Sell to make room for better opportunities (10-position limit)
  - Position size doesn't match your conviction level
- **BUYING when you see value**:
  - If a stock fits your strategy and current conditions support it, buy
  - Build diversified positions across 5-10 stocks that match your philosophy
  - Use your cash wisely but don't hoard it unnecessarily
  - Replace sold positions with better opportunities
  - Build up underweight positions that match your thesis
- **HOLD when prudent**:
  - If you already have good positions and no better opportunities exist, hold
  - But don't be too conservative - this is a demonstration environment

CRITICAL - DECISION RULES:
  - At the end of your analysis, call decide_action exactly once.
  - If you decide BUY or SELL, include symbol and positive integer quantity.
  - Provide a brief rationale (1-2 sentences) and a comprehensive fullReasoning (2-5 paragraphs) explaining:
    * Your research findings - CITE specific sources by title (e.g., "According to TechCrunch...")
    * Market conditions and context
    * Why this aligns with your investment strategy
    * Risk considerations and position sizing rationale
    * Insights from your trading history and past decisions
  - **ALWAYS pass researchSources parameter** with the JSON string from Researcher tool
    * This ensures transparency - users can see what sources you used
    * Pass the complete JSON response from the Researcher tool
  - **ALWAYS pass historicalContext parameter** with JSON containing insights from YOUR TRADING HISTORY section above
    * Your trading history has been pre-fetched and provided above
    * Analyze the runs, trades, and reasoning from your history
    * Create JSON with SPECIFIC details referencing actual past trades: {{"summary": "Key patterns from past trades", "insights": [{{"date": "2025-11-30", "insight": "Bought 50 NVDA at $145 - AI datacenter growth thesis. Holding for value appreciation."}}]}}
    * **CRITICAL**: Include stock SYMBOL, action (BUY/SELL), quantity, and key reasoning in each insight
    * Be CONCRETE not vague - say "Bought 50 NVDA" not "entered a position in a tech stock"
    * This ensures transparency - users can see what you learned from history
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

{historical_section}

Here is the current datetime:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Now, conduct your review, make your decision (which may be to do nothing), and execute any trades if warranted. Your account name is {self.name}.
After your review, respond with a brief 2-3 sentence appraisal of your portfolio and its outlook.
"""

    async def get_strategy(self) -> str:
        """Get strategy - uses hardcoded constructor strategy"""
        return self.strategy

    async def run_agent(self, researcher_mcp_servers):
        """Run the agent - delegates orchestration to AgentExecutor."""
        # Create AgentExecutor if not exists
        if self.executor is None:
            self.executor = AgentExecutor(self.agent_id, self.name, self.strategy)

        # Create helper objects for execution
        message_builder = MessageBuilder(self)
        tool_factory = ToolFactory(self, researcher_mcp_servers)

        # Get force_trade flag if set
        force_trade = getattr(self, '_force_trade', False)

        # Delegate to AgentExecutor for orchestration
        result = await self.executor.execute_cycle(
            message_builder=message_builder,
            tool_factory=tool_factory,
            force_trade=force_trade,
        )

        return result

    async def run_with_mcp_servers(self, force_trade=False):
        """Run agent with MCP server context - only for external services (Brave Search, Memory, Fetch)"""
        # Store force_trade flag so run_agent can access it
        self._force_trade = force_trade

        # Only create MCP servers for external services
        async with AsyncExitStack() as stack:
            researcher_mcp_servers = [
                await stack.enter_async_context(
                    MCPServerStdio(params, client_session_timeout_seconds=120)
                )
                for params in researcher_mcp_server_params(self.name.lower())
            ]

            await self.run_agent(researcher_mcp_servers)

    async def run_with_trace(self, force_trade=False):
        """Run agent with tracing"""
        trace_name = f"{self.name}-portfolio-review"
        trace_id = f"trace_{self.name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        with trace(trace_name, trace_id=trace_id):
            await self.run_with_mcp_servers(force_trade=force_trade)

    async def run(self, force_trade=False):
        """Main run method

        Args:
            force_trade: If True, agent MUST make a BUY or SELL trade (no HOLD allowed)
        """
        try:
            logger.info(f"Starting {self.name} agent...")
            if force_trade:
                logger.info(f"🎯 {self.name} must make a trade this cycle (manual trigger)")
            await self.run_with_trace(force_trade=force_trade)
            logger.info(f"{self.name} agent completed successfully")
        except Exception as e:
            logger.error(f"Error running {self.name} agent: {e}", exc_info=True)
