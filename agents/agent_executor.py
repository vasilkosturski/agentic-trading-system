"""Agent execution orchestration - extracted from SimpleTrader."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Literal

from agents import Agent, Runner

# Import type-safe models
from models import TradingDecision, MarketConditions

# Avoid circular import - only import types for type hints
if TYPE_CHECKING:
    from simple_trader import MessageBuilder, ToolFactory

# Import direct function tools
from trading_tools import (
    initialize_agent,
    buy_shares,
    sell_shares,
    _get_balance_raw,
    _get_holdings_raw,
)
from memory_tools import get_recent_activity

# Import run tracking
from run_tracking import start_run, end_run, mark_run_as_error

# Import status broadcasting
from status_broadcaster import (
    broadcast_status,
    PHASE_INITIALIZING,
    PHASE_RESEARCHING,
    PHASE_DECIDING,
    PHASE_TRADING,
    PHASE_COMPLETED,
    PHASE_ERROR,
)

# Import tool tracking
from tool_tracking import ToolTracker

logger = logging.getLogger(__name__)


class AgentExecutor:
    """Handles agent execution orchestration for trading cycles.

    Responsibilities:
    - Initialize trading cycle (tracking, broadcasting)
    - Prepare context (pre-fetch historical data)
    - Create and run agent
    - Parse agent results and tool usage
    - Execute trading decisions
    - Finalize cycle (end tracking, broadcast status)

    """

    def __init__(self, agent_id: int, name: str, strategy: str):
        """Initialize executor with agent identity.

        Args:
            agent_id: Unique agent identifier
            name: Agent name (e.g., "Warren")
            strategy: Investment strategy description
        """
        self.agent_id = agent_id
        self.name = name
        self.strategy = strategy

        # Per-run execution state
        self.current_run_id: Optional[int] = None
        self.trade_count: int = 0
        self.last_decision: Optional[TradingDecision] = None
        self.tracker: Optional[ToolTracker] = None

    async def execute_cycle(
        self,
        message_builder: "MessageBuilder",
        tool_factory: "ToolFactory",
        force_trade: bool = False,
    ) -> Dict[str, Any]:
        """Execute one complete portfolio review cycle with clear phases.

        Args:
            message_builder: Object that builds agent messages
            tool_factory: Object that creates agent tools
            force_trade: If True, agent must make BUY/SELL (no HOLD)

        Returns:
            Dict with cycle results (decision, trade_count, summary)

        Phases:
        1. Initialize: Start tracking, broadcast status
        2. Prepare context: Pre-fetch historical data
        3. Create agent: Build agent with tools
        4. Run agent: Execute agent with message
        5. Parse results: Extract decision and tool usage
        6. Execute decision: Perform BUY/SELL/HOLD
        7. Finalize: End tracking, broadcast completion
        """
        # Keep "TRADING" for backwards compatibility with backend
        cycle_type = "portfolio review"
        run_type = "TRADING"
        run_id = None

        print(
            f"🤖 {self.name} starting {cycle_type} cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        try:
            # Phase 1: Initialize cycle
            run_id = await self._phase1_initialize(run_type, cycle_type)

            # Phase 2: Prepare context (pre-fetch data)
            context = await self._phase2_prepare_context()

            # Phase 3: Create agent with tools
            agent = await self._phase3_create_agent(tool_factory)

            # Phase 4: Run agent
            result = await self._phase4_run_agent(
                agent, message_builder, context, force_trade
            )

            # Phase 5: Parse results and tool usage
            await self._phase5_parse_results(result)

            # Phase 6: Execute decision
            await self._phase6_execute_decision()

            # Phase 7: Finalize cycle
            await self._phase7_finalize(run_id)

            print(
                f"✅ {self.name} completed {cycle_type} cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            return {
                "decision": self.last_decision,
                "trade_count": self.trade_count,
                "run_id": run_id,
            }

        except Exception as e:
            await self._handle_cycle_error(e, run_id)
            raise

        finally:
            self._cleanup()

    async def _phase1_initialize(self, run_type: str, cycle_type: str) -> int:
        """Phase 1: Initialize agent account, tracking, and broadcasts.

        Args:
            run_type: "TRADING" or "REBALANCE"
            cycle_type: "trading" or "rebalancing"

        Returns:
            run_id for tracking this cycle
        """
        # Initialize agent account (direct function call, not through agent)
        await initialize_agent(self.name)

        if self.agent_id is None:
            raise RuntimeError(
                f"Agent id not set for {self.name}. Use TradingSystem.create() to instantiate."
            )

        # Broadcast: INITIALIZING
        broadcast_status(
            self.agent_id, self.name, PHASE_INITIALIZING, "Starting trading cycle", 0
        )

        # Fetch balance and holdings for logging and run tracking
        balance = await _get_balance_raw(self.agent_id)
        holdings = await _get_holdings_raw(self.agent_id)

        # Market conditions (simplified - could be enhanced)
        market_conditions = MarketConditions(
            timestamp=datetime.now().isoformat(),
            cycle_type=cycle_type,
        )

        # Start run tracking (REQUIRED - every transaction must be linked to a run)
        run_id = await start_run(self.agent_id, self.name, run_type, market_conditions)
        if run_id is None:
            error_msg = f"CRITICAL: Failed to start run tracking for {self.name}. Cannot proceed without runId - every transaction must be linked to a run."
            logger.error(f"🔴 {error_msg}")
            raise Exception(error_msg)

        self.current_run_id = run_id
        self.trade_count = 0
        # NOTE: Don't clear last_decision here - it will be set during agent execution
        # Clearing it breaks testing and there's no benefit to explicitly clearing

        # Initialize tool tracker for transparency
        self.tracker = ToolTracker(run_id)

        # Log initial data access for transparency
        portfolio_info = f"Balance: ${balance:.2f}"
        if holdings:
            # holdings is a List[Dict] with {symbol, quantity, averagePrice}
            symbols = [h["symbol"] for h in holdings[:5]]  # First 5 symbols
            positions_str = ", ".join(symbols) + ("..." if len(holdings) > 5 else "")
            portfolio_info += (
                f", Holdings: {len(holdings)} position(s) ({positions_str})"
            )
        else:
            portfolio_info += ", Holdings: None"

        self.tracker.log_data_access("Portfolio", portfolio_info)

        # Log initialization
        init_text = f"Starting {cycle_type} cycle. Balance: ${balance:.2f}, Positions: {len(holdings)}"
        self.tracker.log_reasoning(
            "initialization", f"Started {cycle_type} cycle", init_text
        )

        return run_id

    async def _phase2_prepare_context(self) -> Dict[str, Any]:
        """Phase 2: Prepare baseline context (recent activity) without steering agent.

        Provides agent with recent trading history as context, but lets agent
        autonomously decide what to research and focus on.

        Returns:
            Dict with historical_context (baseline recent activity)
        """
        # Broadcast: RESEARCHING
        broadcast_status(
            self.agent_id,
            self.name,
            PHASE_RESEARCHING,
            "Preparing context",
            20,
        )

        # Fetch recent activity (last 30 days) as baseline context
        recent_activity_json = await get_recent_activity(self.name, days=30)

        logger.info(f"📊 Baseline context prepared: recent activity (30 days)")

        return {
            "historical_context": recent_activity_json,
        }

    async def _phase3_create_agent(self, tool_factory: "ToolFactory") -> Agent:
        """Phase 3: Create agent with tools.

        Args:
            tool_factory: Object that creates agent tools and researcher

        Returns:
            Agent instance ready to run
        """
        # Delegate to tool_factory to create agent with tools
        # This keeps the executor focused on orchestration, not tool creation
        agent = await tool_factory.create_agent(self)
        return agent

    async def _phase4_run_agent(
        self,
        agent: Agent,
        message_builder: "MessageBuilder",
        context: Dict[str, Any],
        force_trade: bool,
    ) -> Any:
        """Phase 4: Generate message and run agent.

        Args:
            agent: Agent instance to run
            message_builder: Object that builds agent messages
            context: Dict with historical_context (baseline recent activity)
            force_trade: If True, agent must make BUY/SELL (no HOLD)

        Returns:
            Agent result object
        """
        # Generate message with baseline historical context
        message = message_builder.build_message(
            context["historical_context"], force_trade
        )

        result = await Runner.run(agent, message, max_turns=30)
        return result

    async def _phase5_parse_results(self, result) -> None:
        """Phase 5: Parse agent output and track tool usage.

        Args:
            result: Agent result object with new_items (OpenAI Agents SDK v0.2+)

        Updates:
            self.tracker with tool calls and research queries
        """
        research_conducted = False
        # Track tool names by call_id for matching outputs
        tool_name_by_call_id: Dict[str, str] = {}

        logger.info(f"🔍 Agent result type: {type(result)}")
        logger.info(
            f"🔍 Has new_items attr? {hasattr(result, 'new_items') if result else 'result is None'}"
        )
        if result:
            logger.info(f"🔍 Result attributes: {dir(result)}")

        if result and hasattr(result, "new_items"):
            # Parse new_items to extract tool usage (OpenAI Agents SDK v0.2+)
            logger.info(f"📋 Parsing {len(result.new_items)} items from agent result")
            for i, item in enumerate(result.new_items):
                item_type = type(item).__name__
                logger.info(f"  Item #{i}: type={item_type}")

                # DEBUG: Print ALL attributes of this item
                logger.info(f"  🔍 DEBUG - All attributes of {item_type}:")
                for attr in dir(item):
                    if not attr.startswith('_'):  # Skip private attributes
                        try:
                            value = getattr(item, attr)
                            # Skip methods
                            if not callable(value):
                                logger.info(f"    {attr} = {repr(value)[:200]}")
                        except Exception as e:
                            logger.info(f"    {attr} = <error: {e}>")

                # Check if this is a tool call output item
                # Items can have tool_name attribute or be ToolCallOutputItem
                # Try multiple possible attribute names
                tool_name = None
                call_id = None

                # PRIORITY 1: Check raw_item.name (this is where tool name actually is)
                if hasattr(item, 'raw_item') and item.raw_item is not None:
                    raw_item = item.raw_item
                    logger.info(f"  🔍 DEBUG - Found raw_item: {type(raw_item)}")

                    # Check for name in raw_item
                    if hasattr(raw_item, 'name'):
                        potential_name = getattr(raw_item, 'name')
                        logger.info(f"  🔍 DEBUG - raw_item.name = {repr(potential_name)}")
                        if potential_name and isinstance(potential_name, str):
                            tool_name = potential_name
                            logger.info(f"  ✅ Using tool_name from raw_item.name: {tool_name}")

                    # Check for call_id in raw_item
                    if hasattr(raw_item, 'call_id'):
                        call_id = getattr(raw_item, 'call_id')
                        logger.info(f"  🔍 DEBUG - raw_item.call_id = {repr(call_id)}")

                    # For ToolCallOutputItem, raw_item might be a dict
                    if isinstance(raw_item, dict):
                        if 'call_id' in raw_item:
                            call_id = raw_item['call_id']
                            logger.info(f"  🔍 DEBUG - raw_item['call_id'] = {repr(call_id)}")

                # Also check for call_id directly on item (not just raw_item)
                if not call_id and hasattr(item, 'call_id'):
                    call_id = getattr(item, 'call_id')
                    logger.info(f"  🔍 DEBUG - item.call_id = {repr(call_id)}")

                # PRIORITY 2: Try common attribute names for tool name
                if not tool_name:
                    for attr_name in ['tool_name', 'name', 'function_name', 'tool', 'function']:
                        if hasattr(item, attr_name):
                            potential_name = getattr(item, attr_name)
                            logger.info(f"  🔍 DEBUG - Found attribute '{attr_name}' = {repr(potential_name)}")
                            if potential_name and isinstance(potential_name, str):
                                tool_name = potential_name
                                logger.info(f"  ✅ Using tool_name from attribute '{attr_name}': {tool_name}")
                                break

                # PRIORITY 3: If item has 'tool_call' attribute, check inside it
                if not tool_name and hasattr(item, 'tool_call'):
                    tool_call_obj = getattr(item, 'tool_call')
                    logger.info(f"  🔍 DEBUG - Found tool_call object: {type(tool_call_obj)}")
                    for attr_name in ['name', 'function_name', 'tool_name']:
                        if hasattr(tool_call_obj, attr_name):
                            potential_name = getattr(tool_call_obj, attr_name)
                            logger.info(f"  🔍 DEBUG - tool_call.{attr_name} = {repr(potential_name)}")
                            if potential_name and isinstance(potential_name, str):
                                tool_name = potential_name
                                logger.info(f"  ✅ Using tool_name from tool_call.{attr_name}: {tool_name}")
                                break

                # Store tool name by call_id for later matching
                if tool_name and call_id:
                    tool_name_by_call_id[call_id] = tool_name
                    logger.info(f"  📌 Stored mapping: call_id={call_id} -> tool_name={tool_name}")

                # If no tool_name but we have call_id, try to look it up
                if not tool_name and call_id and call_id in tool_name_by_call_id:
                    tool_name = tool_name_by_call_id[call_id]
                    logger.info(f"  🔗 Matched call_id={call_id} to tool_name={tool_name}")

                if tool_name:
                    logger.info(f"  ✅ Found tool call: {tool_name}")

                    # Get tool output - try multiple attributes
                    tool_result_full = ""
                    if hasattr(item, "output"):
                        tool_result_full = str(item.output)
                        logger.info(f"  📤 Got output from 'output' attribute ({len(tool_result_full)} chars)")
                    elif hasattr(item, "content"):
                        tool_result_full = str(item.content)
                        logger.info(f"  📤 Got output from 'content' attribute ({len(tool_result_full)} chars)")
                    elif hasattr(item, "result"):
                        tool_result_full = str(item.result)
                        logger.info(f"  📤 Got output from 'result' attribute ({len(tool_result_full)} chars)")
                    else:
                        logger.warning(f"  ⚠️ No output/content/result attribute found on {item_type}")

                    tool_result = tool_result_full[:300]  # Truncate for logging
                    if self.tracker:
                        self.tracker.log_tool_call(tool_name, {}, tool_result)

                    # Special handling for Researcher tool
                    if tool_name == "Researcher":
                        logger.info(f"  🔍 RESEARCHER TOOL DETECTED!")
                        research_conducted = True

                        # Try to parse JSON response from Researcher
                        sources = []
                        query = "Market research"
                        result_summary = "Research completed"

                        try:
                            # Researcher should return JSON with {"summary": "...", "sources": [...]}
                            research_json = json.loads(tool_result_full)
                            if isinstance(research_json, dict):
                                # Extract sources from JSON
                                if "sources" in research_json and isinstance(research_json["sources"], list):
                                    sources = research_json["sources"]
                                    logger.info(f"  📎 Extracted {len(sources)} sources from Researcher JSON")

                                # Extract summary from JSON
                                if "summary" in research_json:
                                    result_summary = str(research_json["summary"])
                        except json.JSONDecodeError:
                            # Fallback: Try to extract URLs from text if JSON parsing fails
                            logger.info("  ⚠️ Researcher output is not JSON, falling back to URL extraction")
                            sources = self._extract_urls_from_text(tool_result_full)
                            result_summary = self._parse_research_summary(tool_result_full, sources)

                        if sources:
                            logger.info(f"  📎 Found {len(sources)} source URLs")
                            for src in sources[:3]:  # Log first 3
                                logger.info(
                                    f"    - {src.get('title', 'No title')}: {src.get('url', 'No URL')}"
                                )

                        # Try to find the query from previous items
                        # Look backwards for tool call request
                        if i > 0:
                            for j in range(i - 1, max(0, i - 5), -1):  # Check up to 5 items back
                                prev_item = result.new_items[j]
                                # Check if previous item has tool call arguments
                                if hasattr(prev_item, "tool_calls") and prev_item.tool_calls:
                                    for tool_call in prev_item.tool_calls:
                                        if hasattr(tool_call, "name") and tool_call.name == "Researcher":
                                            if hasattr(tool_call, "arguments"):
                                                try:
                                                    args = json.loads(tool_call.arguments) if isinstance(tool_call.arguments, str) else tool_call.arguments
                                                    query = args.get("query", args.get("request", args.get("message", query)))
                                                    if isinstance(query, str):
                                                        query = query[:150]
                                                    break
                                                except:
                                                    pass

                        logger.info(f"  💾 Logging research query with {len(sources)} sources")
                        logger.info(f"    Query: {query[:100]}")
                        logger.info(f"    Summary: {result_summary[:150]}")
                        if self.tracker:
                            self.tracker.log_research_query(query, result_summary, sources)
                else:
                    # No tool_name found
                    logger.warning(f"  ⚠️ No tool_name found for {item_type} - this item will be skipped")

        # Log research phase with actual data
        research_text = "Completed market research and analysis"
        if research_conducted:
            research_text += ". Used Researcher tool to gather current market information."
        if self.tracker:
            self.tracker.log_reasoning("research", "Research completed", research_text)

    async def _phase6_execute_decision(self) -> None:
        """Phase 6: Execute BUY/SELL/HOLD decision and track.

        Reads self.last_decision and executes trade if BUY/SELL.
        """
        # Broadcast: DECIDING (after agent completes reasoning)
        broadcast_status(
            self.agent_id, self.name, PHASE_DECIDING, "Making investment decision", 70
        )

        # Read structured decision from decide_action tool (if any)
        decision = self.last_decision

        # CRITICAL DEBUG: Log what we're about to execute
        logger.error(f"🟡 ABOUT TO EXECUTE: decision={decision}")

        if decision and decision.action in ("BUY", "SELL"):
            # Validate runId is set
            if self.current_run_id is None:
                error_msg = f"CRITICAL: Cannot execute trade - runId is required but not set."
                logger.error(f"🔴 {error_msg}")
                raise Exception(error_msg)

            # Extract decision details (using Pydantic model attributes)
            action = decision.action
            symbol = decision.symbol
            quantity = decision.quantity
            rationale = decision.rationale or "Decision"

            # CRITICAL DEBUG: Log execution details
            logger.error(f"🟢 EXECUTING: {action} {quantity} shares of {symbol}")
            logger.error(f"🟢 RATIONALE: {rationale[:200]}")

            # Log decision with full context
            decision_text = f"{action} {quantity} shares of {symbol}.\n\nRationale: {rationale}"
            if decision.fullReasoning:
                decision_text += f"\n\n{decision.fullReasoning}"
            if self.tracker:
                self.tracker.log_reasoning(
                    "decision", f"Decided: {action} {symbol}", decision_text
                )

            # Broadcast: TRADING
            broadcast_status(
                self.agent_id, self.name, PHASE_TRADING, "Executing trade", 90
            )

            try:
                if action == "BUY":
                    await buy_shares(
                        self.agent_id,
                        symbol,
                        quantity,
                        runId=self.current_run_id,
                        agent_name=self.name,
                    )
                else:
                    await sell_shares(
                        self.agent_id,
                        symbol,
                        quantity,
                        runId=self.current_run_id,
                        agent_name=self.name,
                    )
                self.trade_count += 1

                # Log execution success
                if self.tracker:
                    self.tracker.log_reasoning(
                        "execution",
                        f"Executed {action}",
                        f"Successfully executed {action} {quantity} {symbol}",
                    )
            except Exception as trade_err:
                logger.error(f"Trade execution failed: {trade_err}")

                # Log execution failure
                if self.tracker:
                    self.tracker.log_reasoning(
                        "execution", f"Failed {action}", f"Trade failed: {str(trade_err)}"
                    )
        else:
            # HOLD decision
            summary = decision.rationale if decision else "No decision"
            if not summary:
                summary = "Portfolio unchanged"
            if self.tracker:
                self.tracker.log_reasoning(
                    "decision", "Decided: HOLD", f"No trades. {summary[:200]}"
                )

    async def _phase7_finalize(self, run_id: int) -> None:
        """Phase 7: End run tracking with full context.

        Args:
            run_id: Run ID to finalize
        """
        if run_id is not None:
            # Extract research sources from decision if available
            research_sources = []
            if self.last_decision and self.last_decision.researchSources:
                try:
                    research_sources = json.loads(
                        self.last_decision.researchSources
                    )
                except:
                    research_sources = []

            # Get historical context from decision if available
            historical_context = (
                self.last_decision.historicalContext
                if self.last_decision
                else "{}"
            )

            # Use summary from decision or fallback
            run_summary = (
                self.last_decision.rationale
                if self.last_decision
                else "Agent execution completed"
            )
            if not run_summary:
                run_summary = "Agent execution completed"

            # Use fullReasoning from decision or fallback
            run_full_reasoning = (
                self.last_decision.fullReasoning
                if self.last_decision
                else ""
            )

            await end_run(
                run_id,
                run_summary,
                run_full_reasoning,
                research_sources,
                historical_context,
                self.trade_count,
            )

        # Broadcast: COMPLETED
        outcome_message = (
            f"Completed - {self.trade_count} trade(s) executed"
            if self.trade_count > 0
            else "Completed - No trades (HOLD decision)"
        )
        broadcast_status(
            self.agent_id,
            self.name,
            PHASE_COMPLETED,
            outcome_message,
            100,
            outcome=outcome_message,
        )

    async def _handle_cycle_error(self, error: Exception, run_id: Optional[int]) -> None:
        """Handle cycle execution error.

        Args:
            error: Exception that occurred
            run_id: Run ID if tracking was started
        """
        # Broadcast: ERROR
        broadcast_status(
            self.agent_id,
            self.name,
            PHASE_ERROR,
            f"Error: {str(error)}",
            0,
            outcome=f"Failed: {str(error)}",
        )

        # Mark run as error if tracking was started
        if run_id is not None:
            await mark_run_as_error(run_id, str(error))

    def _cleanup(self) -> None:
        """Clean up execution state after cycle completes or fails."""
        self.current_run_id = None
        self.trade_count = 0
        self.last_decision = None
        self.tracker = None

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
        source_pattern = r"\[SOURCE:\s*([^\]]+)\]\(([^)]+)\)"
        source_citations = re.findall(source_pattern, text)
        for title, url in source_citations:
            if url.startswith("http"):
                sources.append({"title": title.strip(), "url": url.strip()})

        # Pattern 2: Regular markdown links (fallback) - [Title](URL)
        if not sources:
            markdown_links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text)
            for title, url in markdown_links:
                if url.startswith("http") and "SOURCE" not in title:
                    sources.append({"title": title.strip(), "url": url.strip()})

        # Pattern 3: Plain URLs (last resort fallback)
        if not sources:
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            urls = re.findall(url_pattern, text)
            for url in urls[:5]:  # Limit to 5
                # Try to extract domain as title
                domain = url.split("//")[-1].split("/")[0]
                sources.append({"title": domain, "url": url})

        return sources  # Return all SOURCE citations

    def _parse_research_summary(
        self, research_text: str, sources: List[Dict[str, str]]
    ) -> str:
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

        clean_text = re.sub(r"\[SOURCE:[^\]]+\]\([^)]+\)", "", research_text)

        # Get first 250 chars of meaningful content
        lines = [
            line.strip()
            for line in clean_text.split("\n")
            if line.strip() and not line.strip().startswith("http")
        ]
        summary_text = " ".join(lines)[:250].strip()

        if len(" ".join(lines)) > 250:
            summary_text += "..."

        # Add source citation count
        if sources:
            summary_text += (
                f" (Cited {len(sources)} source{'s' if len(sources) != 1 else ''})"
            )

        return summary_text if summary_text else "Research completed"

    def store_decision(
        self,
        action: Literal["BUY", "SELL", "HOLD"],
        symbol: str,
        quantity: int,
        rationale: str,
        full_reasoning: str,
        research_sources: str,
        historical_context: str,
    ) -> None:
        """Store agent's decision for later execution.

        This is called by the decide_action tool during agent execution.
        Uses Pydantic for validation of LLM output.

        Args:
            action: "BUY", "SELL", or "HOLD"
            symbol: Stock symbol
            quantity: Number of shares
            rationale: Brief explanation
            full_reasoning: Complete analysis
            research_sources: JSON string with research sources
            historical_context: JSON string with historical insights

        Raises:
            ValueError: If decision is invalid or inconsistent
        """
        # Create validated decision using Pydantic model
        decision = TradingDecision(
            action=action,
            symbol=symbol,
            quantity=quantity,
            rationale=rationale,
            fullReasoning=full_reasoning,
            researchSources=research_sources or "[]",
            historicalContext=historical_context or "[]",
        )

        # Validate decision consistency
        decision.validate_consistency()

        self.last_decision = decision

        # CRITICAL DEBUG: Log the stored decision
        logger.error(f"🔴 DECISION STORED: {decision.model_dump()}")
