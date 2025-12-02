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

**CRITICAL: You MUST return your findings as a JSON object.**

Your JSON response must have this exact structure:
{{
  "summary": "Brief 2-3 sentence summary of key findings",
  "sources": [
    {{"title": "Article Title", "url": "https://full-url-used.com"}}
  ]
}}

IMPORTANT:
- Only include sources you ACTUALLY USED and found relevant for your findings
- Do NOT include sources you didn't find useful or didn't use
- The summary should synthesize what you learned from ALL the sources combined
- If you didn't find any useful sources, return empty sources array: []

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
- Researcher: Research online for news and opportunities (returns JSON with summary and sources)
- Market data tools: lookup_share_price, get_historical_prices, get_market_indicators
- Memory tools: query_trading_history(symbol, days), query_recent_activity(days)
  - Use these to remember your past decisions and reasoning about stocks
  - Check your history before making decisions to maintain consistency

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
   - The "sources" array contains objects like: {{"title": "Article Title", "url": "https://...", "snippet": "..."}}
   - **CRITICAL**: You MUST pass the COMPLETE JSON from Researcher to decide_action as researchSources
   - Do NOT just copy the summary - include the ENTIRE JSON with the sources array
   - Example: researchSources='{{"summary": "Market analysis...", "sources": [{{"title": "...", "url": "..."}}]}}'

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

    def get_trade_message(self, strategy: str, account: str, historical_context: str = None, research_focus: str = "") -> str:
        """Get trading message with updated instructions, pre-fetched historical context, and research focus"""
        historical_section = ""
        if historical_context:
            historical_section = f"""
---
YOUR TRADING HISTORY (pre-fetched for you):
{historical_context}

Use this historical context to inform your decisions. Reference specific past trades when making new decisions.
---
"""

        research_guidance = ""
        if research_focus:
            research_guidance = f"""
**RESEARCH GUIDANCE**: {research_focus}
When using the Researcher tool, ask it to research these specific stocks based on your portfolio.
"""

        return f"""You are conducting your regular portfolio review and market analysis.

THIS IS A SIMULATION ENVIRONMENT - Be active and demonstrate your trading strategy!
Your goal is to build and manage an interesting portfolio that reflects your investment philosophy.

{research_guidance}

YOUR TRADING APPROACH:
1. Use the Researcher tool to check relevant news and market conditions
   - Researcher returns JSON with summary and sources
   - Save this JSON - you'll need to pass it to decide_action for transparency
2. Review your current holdings - are any underperforming or ready to take profits?
3. Actively look for new opportunities consistent with your strategy
4. Make decisions to either improve your portfolio or capitalize on opportunities

TRADING MINDSET:
- **BE PROACTIVE**: This is your chance to demonstrate your trading style
- **BUILD POSITIONS**: If you have cash and see opportunities aligned with your strategy, take action
- **MANAGE ACTIVELY**: Don't be afraid to adjust positions based on market conditions
- **SELLING is important too**:
  - Sell positions that have broken your investment thesis
  - Take profits on winners that have reached targets
  - Cut losses on underperformers
  - Sell to make room for better opportunities
- **BUYING when you see value**:
  - If a stock fits your strategy and current conditions support it, buy
  - Build diversified positions across 5-10 stocks that match your philosophy
  - Use your cash wisely but don't hoard it unnecessarily
- **HOLD only when portfolio is well-positioned**:
  - If you already have good positions and no better opportunities exist, hold
  - But don't be too conservative - this is a demonstration environment

CRITICAL - DECISION RULES:
  - At the end of your analysis, call decide_action exactly once.
  - If you decide BUY or SELL, include symbol and positive integer quantity.
  - Provide a brief rationale (1-2 sentences) and a comprehensive fullReasoning (2-5 paragraphs) explaining:
    * Your research findings and data sources
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

    def get_rebalance_message(self, strategy: str, account: str, historical_context: str = None, research_focus: str = "") -> str:
        """Get rebalancing message with pre-fetched historical context and research focus"""
        historical_section = ""
        if historical_context:
            historical_section = f"""
---
YOUR TRADING HISTORY (pre-fetched for you):
{historical_context}

Use this to understand your past decisions and maintain consistency in your strategy.
---
"""

        research_guidance = ""
        if research_focus:
            research_guidance = f"""
**RESEARCH GUIDANCE**: {research_focus}
When using the Researcher tool, focus on these stocks from your portfolio.
"""

        return f"""You are conducting a portfolio rebalancing review.

THIS IS A SIMULATION - Actively manage your portfolio to demonstrate your strategy!
Review your positions and make adjustments to keep your portfolio aligned with your investment thesis.

{research_guidance}

YOUR REBALANCING REVIEW:
1. Use the research tool to check news affecting your current holdings
2. Evaluate each position: Does it still fit your strategy and risk tolerance?
3. Check if any positions have grown too large or too small relative to conviction
4. Look for opportunities to optimize your portfolio composition

REBALANCING APPROACH:
- **ACTIVELY MANAGE**: This is your chance to show active portfolio management
- **SELLING criteria**:
  - Position has broken your investment thesis
  - Risk/reward no longer favorable
  - Position size doesn't match your conviction level
  - Better opportunity exists and you need room (10-position limit)
  - Position has achieved profit targets
- **BUYING during rebalance**:
  - Replace sold positions with better opportunities
  - Fill gaps in your strategy execution
  - Add new positions that strengthen your portfolio
  - Build up underweight positions that match your thesis

PORTFOLIO CONSTRAINTS:
- **MAXIMUM 10 POSITIONS AT ANY TIME** - Hard limit enforced by system
- If adding new position during rebalance and at 10 positions, must sell one first
- Adding to existing positions does NOT count toward limit

Your investment strategy:
{strategy}

Here is your current account:
{account}

{historical_section}

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
        async def decide_action(
            action: str,
            symbol: str = None,
            quantity: int = None,
            rationale: str = None,
            fullReasoning: str = None,
            researchSources: str = None,
            historicalContext: str = None
        ) -> str:
            """Record your trading decision with research sources and historical context.

            Args:
                action: BUY, SELL, or HOLD
                symbol: Stock symbol (required for BUY/SELL)
                quantity: Number of shares (required for BUY/SELL)
                rationale: Brief explanation of decision
                fullReasoning: Complete reasoning (optional)
                researchSources: JSON string with research sources from Researcher tool
                historicalContext: JSON string with historical insights from past trades

            Returns:
                Confirmation message
            """
            act = (action or "").upper()

            # CRITICAL DEBUG: Log what agent is passing to decide_action
            logger.error(f"🔴 DECIDE_ACTION CALLED: action={action}, symbol={symbol}, quantity={quantity}")
            logger.error(f"🔴 DECIDE_ACTION RATIONALE: {rationale[:200] if rationale else 'None'}")
            logger.error(f"🔴 RESEARCH SOURCES: {researchSources[:300] if researchSources else 'None'}")

            # VALIDATION: Check if action matches reasoning
            if act in ("BUY", "SELL"):
                if not symbol or not isinstance(quantity, int) or quantity <= 0:
                    raise ValueError("symbol and positive quantity are required for BUY/SELL")

                # Check for mismatch between action and reasoning
                reasoning_text = (rationale or "") + " " + (fullReasoning or "")
                reasoning_lower = reasoning_text.lower()

                if act == "BUY" and ("sell" in reasoning_lower or "selling" in reasoning_lower):
                    error_msg = f"CRITICAL ERROR: action=BUY but reasoning mentions 'sell'. This is a mismatch! Reasoning: {rationale[:100]}"
                    logger.error(f"🚨 {error_msg}")
                    raise ValueError(error_msg)

                if act == "SELL" and ("buy" in reasoning_lower or "buying" in reasoning_lower or "purchase" in reasoning_lower):
                    error_msg = f"CRITICAL ERROR: action=SELL but reasoning mentions 'buy'. This is a mismatch! Reasoning: {rationale[:100]}"
                    logger.error(f"🚨 {error_msg}")
                    raise ValueError(error_msg)
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
                "researchSources": researchSources or "[]",  # Store research sources
                "historicalContext": historicalContext or "[]",  # Store historical insights
            }
            self.last_decision = decision

            # CRITICAL DEBUG: Log the normalized decision
            logger.error(f"🔴 DECISION STORED: {decision}")

            # Return a simple acknowledgement; the system reads self.last_decision
            return "Decision recorded. The system will validate and execute this trade."

        # Memory tools - query past decisions and reasoning
        # Track historical data access for transparency
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
            result = await get_trading_history(self.name, symbol, days)
            # Track that historical data was accessed
            if self.tracker and result:
                summary = result[:150] + "..." if len(result) > 150 else result
                self.tracker.log_data_access(f"Trading History ({symbol})", summary)
            return result
        
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
            result = await get_recent_activity(self.name, days)
            # Track that historical data was accessed
            if self.tracker and result:
                summary = result[:150] + "..." if len(result) > 150 else result
                self.tracker.log_data_access(f"Recent Activity ({days}d)", summary)
            return result

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

        # Start run tracking (REQUIRED - every transaction must be linked to a run)
        run_id = await start_run(self.agent_id, self.name, run_type, market_conditions)
        if run_id is None:
            error_msg = f"CRITICAL: Failed to start run tracking for {self.name}. Cannot proceed without runId - every transaction must be linked to a run."
            logger.error(f"🔴 {error_msg}")
            raise Exception(error_msg)
        
        self.current_run_id = run_id
        self.trade_count = 0
        self.last_decision = None
            
        # Initialize tool tracker for transparency
        self.tracker = ToolTracker(run_id)

        # Log initial data access for transparency
        portfolio_info = f"Balance: ${balance:.2f}"
        if holdings:
            # holdings is a List[Dict] with {symbol, quantity, averagePrice}
            symbols = [h["symbol"] for h in holdings[:5]]  # First 5 symbols
            positions_str = ", ".join(symbols) + ("..." if len(holdings) > 5 else "")
            portfolio_info += f", Holdings: {len(holdings)} position(s) ({positions_str})"
        else:
            portfolio_info += ", Holdings: None"

        self.tracker.log_data_access("Portfolio", portfolio_info)

        # Log initialization
        init_text = f"Starting {cycle_type} cycle. Balance: ${balance:.2f}, Positions: {len(holdings)}"
        self.tracker.log_reasoning("initialization", f"Started {cycle_type} cycle", init_text)

        try:
            # Broadcast: RESEARCHING (combined: fetching data, research, analysis)
            broadcast_status(self.agent_id, self.name, PHASE_RESEARCHING, "Researching and analyzing market opportunities", 30)

            # PRE-FETCH DATA BEFORE AGENT RUNS (more reliable than letting LLM decide to call tools)
            logger.info(f"📊 Pre-fetching historical context for {self.name}")

            # 1. Call get_recent_activity to get trading history (already implemented in memory_tools.py)
            from memory_tools import get_recent_activity
            recent_activity_json = await get_recent_activity(self.name, days=30)

            # 2. Extract stock symbols from recent activity to focus research
            import json
            relevant_symbols = []
            try:
                if recent_activity_json and recent_activity_json != '{"error": "No recent activity found"}':
                    activity_data = json.loads(recent_activity_json)
                    # Extract symbols from trades in the activity data
                    if isinstance(activity_data, dict) and "runs" in activity_data:
                        for run in activity_data.get("runs", [])[:5]:  # Last 5 runs
                            for trade in run.get("trades", []):
                                symbol = trade.get("symbol")
                                if symbol and symbol not in relevant_symbols:
                                    relevant_symbols.append(symbol)
            except Exception as e:
                logger.warning(f"Could not parse recent activity for symbols: {e}")

            # Add current holdings to symbols to research
            if holdings:
                for holding in holdings:
                    symbol = holding.get("symbol")
                    if symbol and symbol not in relevant_symbols:
                        relevant_symbols.append(symbol)

            # Create research context for agent
            research_focus = ""
            if relevant_symbols:
                research_focus = f"Focus your research on these stocks from your portfolio/history: {', '.join(relevant_symbols[:5])}"

            logger.info(f"📊 Research will focus on: {relevant_symbols[:5] if relevant_symbols else 'general market'}")

            # Create agent with direct tools
            self.agent = await self.create_agent(researcher_mcp_servers)

            # Generate message with historical context and research focus pre-injected
            message = (
                self.get_trade_message(strategy, account, recent_activity_json, research_focus)
                if self.do_trade
                else self.get_rebalance_message(strategy, account, recent_activity_json, research_focus)
            )
            
            result = await Runner.run(self.agent, message, max_turns=30)

            # Extract result data and tool usage for transparency
            full_reasoning = ""
            summary = ""
            research_conducted = False

            logger.info(f"🔍 Agent result type: {type(result)}")
            logger.info(f"🔍 Has messages attr? {hasattr(result, 'messages') if result else 'result is None'}")
            if result:
                logger.info(f"🔍 Result attributes: {dir(result)}")

            if result and hasattr(result, 'messages'):
                # Parse messages to extract tool usage
                logger.info(f"📋 Parsing {len(result.messages)} messages from agent result")
                for i, msg in enumerate(result.messages):
                    msg_role = getattr(msg, 'role', 'no_role')
                    msg_type = type(msg).__name__
                    logger.info(f"  Message #{i}: role={msg_role}, type={msg_type}")

                    # Check if this is a tool call message
                    if hasattr(msg, 'role') and msg.role == 'tool':
                        tool_name = getattr(msg, 'name', 'unknown_tool')
                        logger.info(f"  ✅ Found tool call: {tool_name}")
                        tool_result_full = getattr(msg, 'content', '')
                        tool_result = tool_result_full[:300]  # Truncate for logging
                        self.tracker.log_tool_call(tool_name, {}, tool_result)

                        # Special handling for Researcher tool
                        if tool_name == 'Researcher':
                            logger.info(f"  🔍 RESEARCHER TOOL DETECTED!")
                            research_conducted = True

                            # Try to extract URLs from the result
                            sources = self._extract_urls_from_text(tool_result_full)
                            logger.info(f"  📎 Extracted {len(sources)} source URLs from Researcher result")
                            if sources:
                                for src in sources[:3]:  # Log first 3
                                    logger.info(f"    - {src.get('title', 'No title')}: {src.get('url', 'No URL')}")

                            # Try to find the query from the previous message (the assistant's tool call)
                            query = "Market research"
                            if i > 0:
                                prev_msg = result.messages[i-1]
                                if hasattr(prev_msg, 'role') and prev_msg.role == 'assistant':
                                    # Try to extract query from assistant's tool calls or content
                                    prev_content = getattr(prev_msg, 'content', '')
                                    # Check if there are tool_calls in the message
                                    if hasattr(prev_msg, 'tool_calls') and prev_msg.tool_calls:
                                        # Get the first tool call's arguments (this is the actual query)
                                        tool_call = prev_msg.tool_calls[0]
                                        if hasattr(tool_call, 'function') and hasattr(tool_call.function, 'arguments'):
                                            try:
                                                args = json.loads(tool_call.function.arguments)
                                                # Researcher tool typically takes a query/request argument
                                                query = args.get('query', args.get('request', args.get('message', 'Market research')))
                                                if isinstance(query, str):
                                                    query = query[:150]  # Truncate long queries
                                            except:
                                                pass
                                    elif isinstance(prev_content, str) and len(prev_content) > 0:
                                        # Fallback: extract first sentence
                                        query = prev_content.split('\n')[0][:100]

                            # Create better summary from result
                            # Parse the result to extract key insights
                            result_summary = self._parse_research_summary(tool_result_full, sources)

                            logger.info(f"  💾 Logging research query with {len(sources)} sources")
                            logger.info(f"    Query: {query[:100]}")
                            logger.info(f"    Summary: {result_summary[:150]}")
                            self.tracker.log_research_query(query, result_summary, sources)

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

            # Log research phase with actual data (NOW after we've parsed tool usage)
            research_text = "Completed market research and analysis"
            if research_conducted:
                research_text += ". Used Researcher tool to gather current market information."
            self.tracker.log_reasoning("research", "Research completed", research_text)

            # Broadcast: DECIDING (after agent completes reasoning)
            broadcast_status(self.agent_id, self.name, PHASE_DECIDING, "Making investment decision", 70)

            # Read structured decision from decide_action tool (if any) and dispatch deterministically
            decision = self.last_decision
            
            # CRITICAL DEBUG: Log what we're about to execute
            logger.error(f"🟡 ABOUT TO EXECUTE: decision={decision}")
            
            if decision and decision.get("action") in ("BUY", "SELL"):
                # Validate runId is set (REQUIRED - every transaction must be linked to a run)
                if self.current_run_id is None:
                    error_msg = f"CRITICAL: Cannot execute trade - runId is required but not set. Agent must start a run before trading."
                    logger.error(f"🔴 {error_msg}")
                    raise Exception(error_msg)
                
                # Extract decision details
                action = decision["action"]
                symbol = decision["symbol"]
                quantity = int(decision["quantity"])
                rationale = decision.get("rationale") or summary or "Decision"
                
                # CRITICAL DEBUG: Log execution details
                logger.error(f"🟢 EXECUTING: {action} {quantity} shares of {symbol}")
                logger.error(f"🟢 RATIONALE: {rationale[:200]}")

                # Log decision with full context (tracker will add data sources automatically)
                decision_text = f"{action} {quantity} shares of {symbol}.\n\nRationale: {rationale}"
                if decision.get("fullReasoning"):
                    decision_text += f"\n\n{decision['fullReasoning']}"
                self.tracker.log_reasoning("decision", f"Decided: {action} {symbol}", decision_text)
                
                # Broadcast: TRADING
                broadcast_status(self.agent_id, self.name, PHASE_TRADING, "Executing trade", 90)
                # Use fullReasoning from decision if available, otherwise fall back to conversation messages
                decision_full_reasoning = decision.get("fullReasoning") or ""
                final_full_reasoning = decision_full_reasoning if decision_full_reasoning else full_reasoning

                # Get research sources and historical context from decision (agent passed them via decide_action)
                research_sources_json = decision.get("researchSources", "[]")
                historical_context_json = decision.get("historicalContext", "[]")
                
                try:
                    if action == "BUY":
                        await buy_shares(
                            self.agent_id,
                            symbol,
                            quantity,
                            runId=self.current_run_id,
                            agent_name=self.name
                        )
                    else:
                        await sell_shares(
                            self.agent_id,
                            symbol,
                            quantity,
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
                # Extract research sources from decision if available
                research_sources = []
                if decision and decision.get("researchSources"):
                    try:
                        research_sources = json.loads(decision["researchSources"])
                    except:
                        research_sources = []
                
                # Get historical context from decision if available (already a JSON string)
                historical_context = decision.get("historicalContext", "{}") if decision else "{}"
                
                # Use summary from decision or fallback
                run_summary = summary or (rationale if 'rationale' in locals() else "Agent execution completed")
                
                # Use fullReasoning from decision or fallback
                run_full_reasoning = (decision.get("fullReasoning") or "") if decision else (full_reasoning or "Agent execution completed")
                
                await end_run(
                    run_id,
                    run_summary,
                    run_full_reasoning,
                    research_sources,
                    historical_context,
                    self.trade_count
                )

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
            logger.error(f"Error running {self.name} agent: {e}", exc_info=True)
        # Toggle between trading and rebalancing
        self.do_trade = not self.do_trade
