"""Agent execution orchestration - extracted from SimpleTrader.

Uses new phase-based Trading Runs API (/api/runs) for tracking:
- create_run() → POST /api/runs
- update_phase() → PATCH /api/runs/{id}/phase
- complete_run() → PUT /api/runs/{id}/complete
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Protocol

from agents import Agent, Runner


class BuildMessageFn(Protocol):
    """Callback to build the agent prompt message."""
    def __call__(self, historical_context: str, force_trade: bool) -> str: ...


class CreateAgentFn(Protocol):
    """Async callback to create an Agent instance."""
    async def __call__(self, executor: 'AgentExecutor') -> Agent: ...

# Import type-safe models
from models import TradingDecision
from models.run_tracking import (
    CompleteRunData,
    DecisionToolCallDto,
    PhaseStatus,
    ReasoningDto,
    ResearchToolCallDto,
    SourceDto,
    TradeDecision,
)

# Import direct function tools
from trading_tools import (
    initialize_agent,
    buy_shares,
    sell_shares,
    _get_balance_raw,
    _get_holdings_raw,
)
from memory_tools import get_recent_activity

# Import new run tracking
from run_tracking import create_run, update_phase, complete_run

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

    Uses phase-based Trading Runs API for tracking:
    - INITIALIZING: Run created
    - RESEARCHING: Market research phase
    - DECIDING: Trade decision phase
    - TRADING: Trade execution (BUY/SELL only)
    - COMPLETED: Run finished successfully
    - ERROR: Run failed
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

        # Phase timing
        self.research_start_time: Optional[datetime] = None
        self.decision_start_time: Optional[datetime] = None

        # Phase data collection
        self.research_candidates: List[str] = []
        self.research_sources: List[SourceDto] = []
        self.research_tool_calls: List[ResearchToolCallDto] = []
        self.research_notes: str = ""

        self.decision_sources: List[SourceDto] = []
        self.decision_tool_calls: List[DecisionToolCallDto] = []

        # Execution phase data
        self.trade_id: Optional[int] = None
        self.execution_status: Optional[PhaseStatus] = None
        self.execution_error: Optional[str] = None

    async def execute_cycle(
        self,
        build_message_fn: BuildMessageFn,
        create_agent_fn: CreateAgentFn,
        force_trade: bool = False,
    ) -> Dict[str, Any]:
        """Execute one complete portfolio review cycle with clear phases.

        Args:
            build_message_fn: Function that builds agent message (historical_context, force_trade) -> str
            create_agent_fn: Async function that creates agent (executor) -> Agent
            force_trade: If True, agent must make BUY/SELL (no HOLD)

        Returns:
            Dict with cycle results (decision, trade_count, summary)

        Phases:
        1. Initialize: Create run, update to RESEARCHING
        2. Prepare context: Pre-fetch historical data
        3. Create agent: Build agent with tools
        4. Run agent: Execute agent with message
        5. Parse results: Extract decision, update to DECIDING
        6. Execute decision: Update to TRADING (if BUY/SELL), execute trade
        7. Finalize: Complete run with all phase data
        """
        run_id = None

        print(
            f"🤖 {self.name} starting portfolio review at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        try:
            # Phase 1: Start run tracking and setup
            run_id = await self._phase1_start_run()

            # Phase 2: Prepare context (pre-fetch data)
            context = await self._phase2_prepare_context()

            # Phase 3: Create agent with tools
            agent = await self._phase3_create_agent(create_agent_fn)

            # Phase 4: Run agent
            result = await self._phase4_run_agent(
                agent, build_message_fn, context, force_trade
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

    async def _phase1_start_run(self) -> int:
        """Phase 1: Create run and transition to RESEARCHING.

        Returns:
            run_id for tracking this cycle

        Raises:
            RuntimeError: If agent_id is not set
            Exception: If run creation fails
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

        # Create run via new API (POST /api/runs)
        run_id = await create_run(self.agent_id)
        if run_id is None:
            error_msg = f"CRITICAL: Failed to create run for {self.name}. Cannot proceed without runId."
            logger.error(f"🔴 {error_msg}")
            raise Exception(error_msg)

        self.current_run_id = run_id
        self.trade_count = 0

        # Update to RESEARCHING phase
        await update_phase(run_id, "RESEARCHING")
        self.research_start_time = datetime.now()

        # Broadcast: RESEARCHING
        broadcast_status(
            self.agent_id, self.name, PHASE_RESEARCHING, "Researching market", 20
        )

        # Initialize tool tracker for local data collection
        self.tracker = ToolTracker(run_id)

        # Fetch balance and holdings for logging
        balance = await _get_balance_raw(self.agent_id)
        holdings = await _get_holdings_raw(self.agent_id)

        # Log initial data access for transparency
        portfolio_info = f"Balance: ${balance:.2f}"
        if holdings:
            symbols = [h.symbol for h in holdings[:5]]
            positions_str = ", ".join(symbols) + ("..." if len(holdings) > 5 else "")
            portfolio_info += f", Holdings: {len(holdings)} position(s) ({positions_str})"
        else:
            portfolio_info += ", Holdings: None"

        self.tracker.log_data_access("Portfolio", portfolio_info)

        # Add system context source
        self.research_sources.append(
            SourceDto.system_context(f"Portfolio context: {portfolio_info}")
        )

        return run_id

    async def _phase2_prepare_context(self) -> Dict[str, Any]:
        """Phase 2: Prepare baseline context (recent activity).

        Returns:
            Dict with historical_context (baseline recent activity)
        """
        # Fetch recent activity (last 30 days) as baseline context
        recent_activity_json = await get_recent_activity(self.name, days=30)

        logger.info(f"📊 Baseline context prepared: recent activity (30 days)")

        # Add system context source for recent activity
        self.research_sources.append(
            SourceDto.system_context("Retrieved 30-day trading activity history")
        )

        return {
            "historical_context": recent_activity_json,
        }

    async def _phase3_create_agent(self, create_agent_fn: CreateAgentFn) -> Agent:
        """Phase 3: Create agent with tools.

        Args:
            create_agent_fn: Async function that creates agent with tools

        Returns:
            Agent instance ready to run
        """
        agent = await create_agent_fn(self)
        return agent

    async def _phase4_run_agent(
        self,
        agent: Agent,
        build_message_fn: BuildMessageFn,
        context: Dict[str, Any],
        force_trade: bool,
    ) -> Any:
        """Phase 4: Generate message and run agent.

        Args:
            agent: Agent instance to run
            build_message_fn: Function that builds agent message
            context: Dict with historical_context (baseline recent activity)
            force_trade: If True, agent must make BUY/SELL (no HOLD)

        Returns:
            Agent result object
        """
        message = build_message_fn(context["historical_context"], force_trade)
        result = await Runner.run(agent, message, max_turns=30)
        return result

    async def _phase5_parse_results(self, result) -> None:
        """Phase 5: Parse agent output, collect research data, transition to DECIDING.

        Args:
            result: Agent result object with new_items (OpenAI Agents SDK)
        """
        # Calculate research latency
        research_latency_ms = None
        if self.research_start_time:
            research_latency_ms = int(
                (datetime.now() - self.research_start_time).total_seconds() * 1000
            )

        # Update to DECIDING phase
        if self.current_run_id:
            await update_phase(self.current_run_id, "DECIDING")
        self.decision_start_time = datetime.now()

        # Broadcast: DECIDING
        broadcast_status(
            self.agent_id, self.name, PHASE_DECIDING, "Making investment decision", 70
        )

        research_conducted = False
        tool_name_by_call_id: Dict[str, str] = {}

        if not result or not hasattr(result, "new_items"):
            logger.warning("No new_items in agent result - skipping tool parsing")
            return

        logger.info(f"📋 Parsing {len(result.new_items)} items from agent result")

        for i, item in enumerate(result.new_items):
            tool_name = None
            call_id = None

            # Extract tool name and call_id from raw_item
            if hasattr(item, 'raw_item') and item.raw_item is not None:
                raw_item = item.raw_item
                if hasattr(raw_item, 'name'):
                    name = getattr(raw_item, 'name')
                    if name and isinstance(name, str):
                        tool_name = name
                if hasattr(raw_item, 'call_id'):
                    call_id = getattr(raw_item, 'call_id')

            if not call_id and hasattr(item, 'call_id'):
                call_id = getattr(item, 'call_id')

            if tool_name and call_id:
                tool_name_by_call_id[call_id] = tool_name

            if not tool_name and call_id and call_id in tool_name_by_call_id:
                tool_name = tool_name_by_call_id[call_id]

            if not tool_name:
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

            # Track research tool calls
            self.research_tool_calls.append(
                ResearchToolCallDto(tool=tool_name, durationMs=None)
            )

            # Special handling for Researcher tool - extract sources
            if tool_name == "Researcher":
                research_conducted = True
                self._process_researcher_output(tool_result_full, result.new_items, i)

        # Build research notes
        if research_conducted:
            research_count = len(self.tracker.research_queries) if self.tracker else 0
            if research_count > 1:
                self.research_notes = f"Conducted {research_count} research queries."
            else:
                self.research_notes = "Completed market research and analysis."
        else:
            self.research_notes = "Analysis completed without external research."

        if self.tracker:
            self.tracker.log_reasoning("research", "Research completed", self.research_notes)

    async def _phase6_execute_decision(self) -> None:
        """Phase 6: Execute BUY/SELL/HOLD decision.

        Updates to TRADING phase for BUY/SELL, captures execution result.
        """
        decision = self.last_decision

        logger.info(f"🟡 ABOUT TO EXECUTE: decision={decision}")

        if decision and decision.action in ("BUY", "SELL"):
            if self.current_run_id is None:
                error_msg = "CRITICAL: Cannot execute trade - runId is required but not set."
                logger.error(f"🔴 {error_msg}")
                raise Exception(error_msg)

            action = decision.action
            symbol = decision.symbol
            quantity = decision.quantity
            rationale = decision.rationale or "Decision"

            logger.info(f"🟢 EXECUTING: {action} {quantity} shares of {symbol}")

            # Update to TRADING phase
            await update_phase(self.current_run_id, "TRADING")

            # Broadcast: TRADING
            broadcast_status(
                self.agent_id, self.name, PHASE_TRADING, "Executing trade", 90
            )

            try:
                if action == "BUY":
                    result = await buy_shares(
                        self.agent_id,
                        symbol,
                        quantity,
                        runId=self.current_run_id,
                        agent_name=self.name,
                    )
                else:
                    result = await sell_shares(
                        self.agent_id,
                        symbol,
                        quantity,
                        runId=self.current_run_id,
                        agent_name=self.name,
                    )

                self.trade_count += 1
                self.execution_status = PhaseStatus.COMPLETED
                # Capture trade_id from result for audit trail
                self.trade_id = result.tradeId

                if self.tracker:
                    self.tracker.log_reasoning(
                        "execution",
                        f"Executed {action}",
                        f"Successfully executed {action} {quantity} {symbol}",
                    )

            except Exception as trade_err:
                logger.error(f"Trade execution failed: {trade_err}")
                self.execution_status = PhaseStatus.FAILED
                self.execution_error = str(trade_err)

                if self.tracker:
                    self.tracker.log_reasoning(
                        "execution", f"Failed {action}", f"Trade failed: {str(trade_err)}"
                    )
        else:
            # HOLD decision - no trade execution
            self.execution_status = PhaseStatus.SKIPPED
            summary = decision.rationale if decision else "No decision"
            if self.tracker:
                self.tracker.log_reasoning(
                    "decision", "Decided: HOLD", f"No trades. {summary[:200] if summary else ''}"
                )

    async def _phase7_finalize(self, run_id: int) -> None:
        """Phase 7: Complete run with all phase data.

        Args:
            run_id: Run ID to finalize
        """
        if run_id is None:
            return

        # Calculate decision latency
        decision_latency_ms = None
        if self.decision_start_time:
            decision_latency_ms = int(
                (datetime.now() - self.decision_start_time).total_seconds() * 1000
            )

        # Calculate research latency
        research_latency_ms = None
        if self.research_start_time and self.decision_start_time:
            research_latency_ms = int(
                (self.decision_start_time - self.research_start_time).total_seconds() * 1000
            )

        # Determine trade decision
        decision = self.last_decision
        trade_decision = TradeDecision.HOLD
        symbol = None
        quantity = None

        if decision:
            if decision.action == "BUY":
                trade_decision = TradeDecision.BUY
            elif decision.action == "SELL":
                trade_decision = TradeDecision.SELL
            symbol = decision.symbol if decision.action in ("BUY", "SELL") else None
            quantity = decision.quantity if decision.action in ("BUY", "SELL") else None

        # Build reasoning DTO from decision
        reasoning = None
        if decision and decision.fullReasoning:
            reasoning = ReasoningDto(
                portfolioContext=None,
                historicalContext=None,
                researchSummary=None,
                candidateEvaluation=None,
                finalRationale=decision.fullReasoning[:2000]  # Truncate if too long
            )

        # Build CompleteRunData
        complete_data = CompleteRunData(
            # Research phase
            candidates=self.research_candidates,
            researchSources=self.research_sources,
            researchNotes=self.research_notes,
            researchToolCalls=self.research_tool_calls,
            researchLatencyMs=research_latency_ms,
            # Decision phase
            decision=trade_decision,
            symbol=symbol,
            quantity=quantity,
            reasoning=reasoning,
            decisionSources=self.decision_sources,
            decisionToolCalls=self.decision_tool_calls,
            decisionLatencyMs=decision_latency_ms,
            # Execution phase
            tradeId=self.trade_id,
            executionStatus=self.execution_status,
            errorDetails=self.execution_error,
        )

        # Complete the run via new API
        await complete_run(run_id, complete_data)

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

        # Update run to ERROR phase and complete with error details
        if run_id is not None:
            await update_phase(run_id, "ERROR")

            # Complete with partial data and error
            error_data = CompleteRunData(
                decision=TradeDecision.HOLD,  # Safe default
                executionStatus=PhaseStatus.FAILED,
                errorDetails=str(error)[:500],
            )
            await complete_run(run_id, error_data)

    def _cleanup(self) -> None:
        """Clean up execution state after cycle completes or fails."""
        self.current_run_id = None
        self.trade_count = 0
        self.last_decision = None
        self.tracker = None

        # Reset timing
        self.research_start_time = None
        self.decision_start_time = None

        # Reset phase data
        self.research_candidates = []
        self.research_sources = []
        self.research_tool_calls = []
        self.research_notes = ""
        self.decision_sources = []
        self.decision_tool_calls = []
        self.trade_id = None
        self.execution_status = None
        self.execution_error = None

    def _process_researcher_output(
        self, tool_result: str, items: list, current_index: int
    ) -> None:
        """Process Researcher tool output - extract sources and candidates.

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
                # Extract candidates if present
                if "candidates" in research_json and isinstance(research_json["candidates"], list):
                    for candidate in research_json["candidates"]:
                        if isinstance(candidate, str) and candidate not in self.research_candidates:
                            self.research_candidates.append(candidate)
        except json.JSONDecodeError:
            sources = self._extract_urls_from_text(tool_result)
            result_summary = self._parse_research_summary(tool_result, sources)

        # Try to find the original query
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

        # Add web sources to research_sources
        for source in sources:
            if isinstance(source, dict):
                url = source.get("url")
                if url:
                    self.research_sources.append(
                        SourceDto.web(
                            title=source.get("title", "Article"),
                            url=str(url)
                        )
                    )

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
            for url in urls[:5]:
                domain = url.split("//")[-1].split("/")[0]
                sources.append({"title": domain, "url": url})

        return sources

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

        import re
        clean_text = re.sub(r"\[SOURCE:[^\]]+\]\([^)]+\)", "", research_text)

        lines = [
            line.strip()
            for line in clean_text.split("\n")
            if line.strip() and not line.strip().startswith("http")
        ]
        summary_text = " ".join(lines)[:250].strip()

        if len(" ".join(lines)) > 250:
            summary_text += "..."

        if sources:
            summary_text += f" (Cited {len(sources)} source{'s' if len(sources) != 1 else ''})"

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

        logger.info(f"🔴 DECISION STORED: action={action}, symbol={symbol}, quantity={quantity}")
