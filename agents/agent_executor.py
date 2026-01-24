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

# Import type-safe models
from models import TradingDecision, ResearchResponse
from pydantic import ValidationError
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

# Import SDK parsing utilities
from utils.sdk_parser import (
    TOOL_RESEARCHER,
    extract_tool_calls,
)

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

# Import two-agent architecture
from market_analyst import create_market_analyst_agent, build_research_prompt
from decision_maker import create_decision_maker_agent, build_decision_prompt

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

    def __init__(
        self,
        agent_id: int,
        name: str,
        agent_style: str,
        strategy: str,
        model_name: str = "gpt-4o-mini",
    ):
        """Initialize executor with agent identity.

        Args:
            agent_id: Unique agent identifier
            name: Agent name (e.g., "Warren")
            agent_style: Investment style (e.g., "Value Investor")
            strategy: Investment strategy description
            model_name: Model to use for agents (default: gpt-4o-mini)
        """
        self.agent_id = agent_id
        self.name = name
        self.agent_style = agent_style
        self.strategy = strategy
        self.model_name = model_name

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

        # Execution phase data
        self.trade_id: Optional[int] = None
        self.execution_status: Optional[PhaseStatus] = None
        self.execution_error: Optional[str] = None

    async def execute_cycle(
        self,
        mcp_pool,  # MCPPool
        force_trade: bool = False,
    ) -> Dict[str, Any]:
        """Execute one complete portfolio review cycle with TWO-AGENT architecture.

        Args:
            mcp_pool: MCP pool for creating agents
            force_trade: If True, agent must make BUY/SELL (no HOLD)

        Returns:
            Dict with cycle results (decision, trade_count, summary)

        Phases (two-agent architecture):
        1. Initialize: Create run, update to RESEARCHING
        2. Prepare context: Pre-fetch historical data
        3. Run Market Analyst: Research phase (RESEARCHING)
        4. Run Decision Maker: Decision phase (DECIDING)
        5. Validate results: Ensure decision was recorded
        6. Execute decision: Update to TRADING (if BUY/SELL), execute trade
        7. Finalize: Complete run with all phase data

        Note: Old Phase 3 "Create agent" removed - agents now created in Phases 3 & 4
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

            # Phase 3: Run Market Analyst (RESEARCHING phase)
            research_response = await self._phase3_run_market_analyst(
                mcp_pool, context
            )

            # Phase 4: Run Decision Maker (DECIDING phase)
            await self._phase4_run_decision_maker(
                mcp_pool, research_response, context, force_trade
            )

            # Phase 5: Validate results (decision already stored by decide_action tool)
            await self._phase5_validate_results()

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

    async def _phase3_run_market_analyst(
        self, mcp_pool, context: Dict[str, Any]
    ) -> ResearchResponse:
        """Phase 3: Run Market Analyst agent (RESEARCHING phase).

        Args:
            mcp_pool: MCP pool for creating agent
            context: Dict with account data

        Returns:
            ResearchResponse with candidates and sources
        """
        # Get current account state for research context
        balance = await _get_balance_raw(self.agent_id)
        holdings = await _get_holdings_raw(self.agent_id)
        position_count = len(holdings)

        # Build holdings summary
        if holdings:
            symbols = [h.symbol for h in holdings[:5]]
            holdings_summary = ", ".join(symbols) + ("..." if len(holdings) > 5 else "")
        else:
            holdings_summary = "None"

        # Create Market Analyst agent
        analyst = await create_market_analyst_agent(
            agent_name=self.name,
            agent_style=self.agent_style,
            strategy=self.strategy,
            mcp_pool=mcp_pool,
            model_name=self.model_name,
        )

        # Build research prompt
        research_prompt = build_research_prompt(
            agent_name=self.name,
            agent_style=self.agent_style,
            balance=balance,
            position_count=position_count,
            max_positions=10,
            holdings_summary=holdings_summary,
            historical_context=context.get("historical_context", "{}"),
            force_trade=False,  # Research phase doesn't care about force_trade
        )

        logger.info(f"🔬 Running Market Analyst for {self.name}...")

        # Run Market Analyst
        result = await Runner.run(analyst, research_prompt, max_turns=30)

        # Extract ResearchResponse from result
        if hasattr(result, 'output') and result.output:
            research_response = result.output  # Already typed as ResearchResponse
        else:
            # Fallback if output not typed
            logger.warning("Market Analyst result missing typed output, using empty response")
            research_response = ResearchResponse(
                summary="Research phase completed with no output",
                sources=[],
            )

        # Collect research phase data
        self.research_candidates = getattr(research_response, 'candidates', []) if hasattr(research_response, 'candidates') else []
        self.research_sources = [
            SourceDto(
                type="web",
                title=source.title,
                url=source.url,
            )
            for source in research_response.sources
        ]
        self.research_notes = research_response.summary

        # Calculate research latency
        if self.research_start_time:
            research_latency_ms = int(
                (datetime.now() - self.research_start_time).total_seconds() * 1000
            )
            logger.info(f"📊 Market Analyst completed in {research_latency_ms}ms")

        logger.info(
            f"✅ Market Analyst found {len(self.research_candidates)} candidates with {len(self.research_sources)} sources"
        )

        return research_response

    async def _phase4_run_decision_maker(
        self,
        mcp_pool,
        research_response: ResearchResponse,
        context: Dict[str, Any],
        force_trade: bool,
    ) -> None:
        """Phase 4: Run Decision Maker agent (DECIDING phase).

        Args:
            mcp_pool: MCP pool for creating agent
            research_response: Market Analyst research results
            context: Dict with historical_context
            force_trade: If True, agent must make BUY/SELL (no HOLD)
        """
        # Update to DECIDING phase
        if self.current_run_id:
            await update_phase(self.current_run_id, "DECIDING")
        self.decision_start_time = datetime.now()

        # Broadcast: DECIDING
        broadcast_status(
            self.agent_id, self.name, PHASE_DECIDING, "Making investment decision", 70
        )

        # Get current account state
        balance = await _get_balance_raw(self.agent_id)
        holdings = await _get_holdings_raw(self.agent_id)
        position_count = len(holdings)

        # Build holdings summary
        if holdings:
            symbols = [h.symbol for h in holdings[:5]]
            holdings_summary = ", ".join(symbols) + ("..." if len(holdings) > 5 else "")
        else:
            holdings_summary = "None"

        # Create Decision Maker agent
        trader = await create_decision_maker_agent(
            agent_name=self.name,
            agent_style=self.agent_style,
            strategy=self.strategy,
            executor=self,
            mcp_pool=mcp_pool,
            model_name=self.model_name,
        )

        # Build decision prompt
        decision_prompt = build_decision_prompt(
            agent_name=self.name,
            agent_style=self.agent_style,
            research_response=research_response,
            balance=balance,
            position_count=position_count,
            max_positions=10,
            holdings_summary=holdings_summary,
            historical_context=context.get("historical_context", ""),
            force_trade=force_trade,
        )

        logger.info(f"🧠 Running Decision Maker for {self.name}...")

        # Run Decision Maker agent
        result = await Runner.run(trader, decision_prompt, max_turns=30)

        # Decision is already stored by decide_action tool in self.last_decision
        if not self.last_decision:
            raise RuntimeError(
                f"{self.name} completed decision phase but did not call decide_action tool"
            )

        logger.info(
            f"✅ Decision Maker: {self.last_decision.action} {self.last_decision.symbol or ''}"
        )

        # Calculate decision latency
        if self.decision_start_time:
            decision_latency_ms = int(
                (datetime.now() - self.decision_start_time).total_seconds() * 1000
            )
            logger.info(f"📊 Decision Maker completed in {decision_latency_ms}ms")

    async def _phase5_validate_results(self) -> None:
        """Phase 5: Validate results from two-agent flow.

        In the two-agent architecture, all data collection is done in Phase 3 and 4.
        This phase just validates that we have a decision.
        """
        # Validate we have a decision
        if not self.last_decision:
            raise RuntimeError(
                f"{self.name} reached Phase 5 but no decision was recorded. "
                "Decision Maker agent should have called decide_action tool."
            )

        logger.info(
            f"✅ Phase 5: Validated decision: {self.last_decision.action} "
            f"{self.last_decision.symbol or ''}"
        )

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

        # Parse typed ResearchResponse from Researcher (enforced by output_type)
        try:
            research = ResearchResponse.model_validate_json(tool_result)
            result_summary = research.summary
            # Convert ResearchSource objects to dicts for backwards compatibility
            sources = [{"title": src.title, "url": src.url} for src in research.sources]
        except ValidationError as e:
            logger.error(f"Failed to parse ResearchResponse (should not happen with output_type): {e}")
            # If this happens, the SDK's output_type enforcement failed
            result_summary = "Research completed (parsing failed)"
            sources = []

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
