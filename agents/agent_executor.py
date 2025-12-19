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
        run_type = "TRADING"  # Backend expects this for run categorization
        run_id = None

        print(
            f"🤖 {self.name} starting portfolio review at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        try:
            # Phase 1: Start run tracking and setup
            run_id = await self._phase1_start_run(run_type)

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
                f"✅ {self.name} completed portfolio review at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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

    async def _phase1_start_run(self, run_type: str) -> int:
        """Phase 1: Start a tracked run and initialize agent state.

        Initializes agent account, starts backend run tracking, and sets up
        tool tracking for transparency. Every trade must be linked to a run.

        Args:
            run_type: "TRADING" (sent to backend for run categorization)

        Returns:
            run_id for tracking this cycle

        Raises:
            RuntimeError: If agent_id is not set
            Exception: If run tracking fails to start
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

        # Market conditions (timestamp for run tracking)
        market_conditions = MarketConditions(
            timestamp=datetime.now().isoformat(),
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
            # holdings is List[Holding] with typed attributes
            symbols = [h.symbol for h in holdings[:5]]  # First 5 symbols
            positions_str = ", ".join(symbols) + ("..." if len(holdings) > 5 else "")
            portfolio_info += (
                f", Holdings: {len(holdings)} position(s) ({positions_str})"
            )
        else:
            portfolio_info += ", Holdings: None"

        self.tracker.log_data_access("Portfolio", portfolio_info)

        # Log initialization
        init_text = f"Starting portfolio review. Balance: ${balance:.2f}, Positions: {len(holdings)}"
        self.tracker.log_reasoning(
            "initialization", "Started portfolio review", init_text
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
            result: Agent result object with new_items (OpenAI Agents SDK v0.2.4)

        Updates:
            self.tracker with tool calls and research queries

        Note:
            Tool parsing relies on SDK v0.2.4 structure. If SDK is updated,
            this method may need adjustment. See requirements.txt for pinned version.
        """
        research_conducted = False
        # Track tool names by call_id for matching outputs to their tool calls
        tool_name_by_call_id: Dict[str, str] = {}

        if not result or not hasattr(result, "new_items"):
            logger.warning("No new_items in agent result - skipping tool parsing")
            return

        logger.info(f"📋 Parsing {len(result.new_items)} items from agent result")

        for i, item in enumerate(result.new_items):
            item_type = type(item).__name__
            tool_name = None
            call_id = None

            # Extract tool name and call_id from raw_item (SDK v0.2.4 structure)
            if hasattr(item, 'raw_item') and item.raw_item is not None:
                raw_item = item.raw_item

                # Tool name is in raw_item.name
                if hasattr(raw_item, 'name'):
                    name = getattr(raw_item, 'name')
                    if name and isinstance(name, str):
                        tool_name = name

                # Call ID for matching tool calls to outputs
                if hasattr(raw_item, 'call_id'):
                    call_id = getattr(raw_item, 'call_id')

            # Fallback: call_id directly on item
            if not call_id and hasattr(item, 'call_id'):
                call_id = getattr(item, 'call_id')

            # Build call_id -> tool_name mapping for output items
            if tool_name and call_id:
                tool_name_by_call_id[call_id] = tool_name

            # If we have call_id but no tool_name, look up from mapping
            if not tool_name and call_id and call_id in tool_name_by_call_id:
                tool_name = tool_name_by_call_id[call_id]

            if not tool_name:
                # Not a tool call item (e.g., message item) - skip silently
                continue

            logger.info(f"  🔧 Tool call: {tool_name}")

            # Extract tool output
            tool_result_full = ""
            if hasattr(item, "output"):
                tool_result_full = str(item.output)
            elif hasattr(item, "content"):
                tool_result_full = str(item.content)

            # Log tool call for audit trail
            if self.tracker:
                self.tracker.log_tool_call(tool_name, {}, tool_result_full[:300])

            # Special handling for Researcher tool - extract sources
            if tool_name == "Researcher":
                research_conducted = True
                self._process_researcher_output(
                    tool_result_full, result.new_items, i
                )

        # Log research phase completion
        if research_conducted:
            research_count = len(self.tracker.research_queries) if self.tracker else 0
            if research_count > 1:
                research_text = f"Completed market research - conducted {research_count} research queries to gather comprehensive information."
            else:
                research_text = "Completed market research and analysis. Used Researcher tool to gather current market information."
        else:
            research_text = "Completed analysis without external research."

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

    def _process_researcher_output(
        self, tool_result: str, items: list, current_index: int
    ) -> None:
        """Process Researcher tool output - extract sources and log research query.

        Args:
            tool_result: Full output from Researcher tool
            items: List of all items from agent result (for query extraction)
            current_index: Index of current item in items list
        """
        sources = []
        query = "Market research"
        result_summary = "Research completed"

        # Try to parse JSON response from Researcher
        try:
            research_json = json.loads(tool_result)
            if isinstance(research_json, dict):
                if "sources" in research_json and isinstance(research_json["sources"], list):
                    sources = research_json["sources"]
                if "summary" in research_json:
                    result_summary = str(research_json["summary"])
        except json.JSONDecodeError:
            # Fallback: Extract URLs from text if not JSON
            sources = self._extract_urls_from_text(tool_result)
            result_summary = self._parse_research_summary(tool_result, sources)

        # Try to find the original query from previous items
        if current_index > 0:
            for j in range(current_index - 1, max(0, current_index - 5), -1):
                prev_item = items[j]
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
                                except (json.JSONDecodeError, TypeError):
                                    pass

        if sources:
            logger.info(f"  📎 Research: {len(sources)} sources, query: {query[:50]}...")

        if self.tracker:
            self.tracker.log_research_query(query, result_summary, sources)

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
