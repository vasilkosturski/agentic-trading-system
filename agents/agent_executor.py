"""Agent execution orchestration - extracted from SimpleTrader.

Uses Trading Runs API (/api/runs) for tracking:
- create_run() → POST /api/runs
- update_phase() → PATCH /api/runs/{id}/phase
- complete_run() → PUT /api/runs/{id}/complete

Architecture:
- Sequential operations with explicit parameters and typed results
- Orchestrator assembles results into final state
- Fail-fast error handling (no silent fallbacks)
"""

import json
import logging
from datetime import datetime
from typing import Optional

from agents import Runner

from models import TradingDecision, ResearchResponse, CycleResult
from models.orchestration import (
    AccountData,
    RunContext,
    ResearchResult,
    DecisionResult,
    ExecutionResult,
)
from models.api_responses import RecentActivityResponse
from models.run_tracking import (
    CompleteRunData,
    DecisionPhaseData,
    ExecutionPhaseData,
    PhaseStatus,
    ReasoningDto,
    ResearchPhaseData,
    RunPhase,
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

# Import SDK parsing for tool call extraction
from utils.sdk_parser import extract_tool_calls
from models.run_tracking import ToolCallDto

# Import two-agent architecture (OO classes with typed inputs)
from market_analyst import MarketAnalyst, MarketAnalystContext
from decision_maker import DecisionMaker, DecisionContext

logger = logging.getLogger(__name__)


class AgentExecutor:
    """Handles agent execution orchestration for trading cycles.

    Uses Trading Runs API for tracking:
    - INITIALIZING: Run created
    - RESEARCHING: Market research phase
    - DECIDING: Trade decision phase
    - TRADING: Trade execution (BUY/SELL only)
    - COMPLETED: Run finished successfully
    - ERROR: Run failed
    
    Data Flow:
    - RunContext created at start with guaranteed non-None values
    - Context passed through all operations explicitly
    - No instance variables for per-run state (only agent identity)
    """

    def __init__(
        self,
        agent_id: int,
        name: str,
        agent_style: str,
        model_name: str = "gpt-4o-mini",
    ):
        """Initialize executor with agent identity.

        Args:
            agent_id: Unique agent identifier
            name: Agent name (e.g., "Warren")
            agent_style: Investment style (e.g., "Value Investor")
            model_name: Model to use for agents (default: gpt-4o-mini)
        """
        # Agent identity (immutable for lifetime of executor)
        self.agent_id = agent_id
        self.name = name
        self.agent_style = agent_style
        self.model_name = model_name

    async def execute_cycle(
        self,
        mcp_pool,  # MCPPool
        force_trade: bool = False,
    ) -> CycleResult:
        """Execute one complete portfolio review cycle with TWO-AGENT architecture.

        Args:
            mcp_pool: MCP pool for creating agents
            force_trade: If True, agent must make BUY/SELL (no HOLD)

        Returns:
            CycleResult with decision, trade_count, and run_id

        Architecture: Sequential operations with explicit parameters and typed results.
        Orchestrator assembles results into RunContext for tracking.
        """
        ctx: Optional[RunContext] = None

        print(
            f"🤖 {self.name} starting portfolio review at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        try:
            # === INITIALIZATION ===
            # Set timing at orchestrator level (not buried in helper)
            research_start_time = datetime.now()
            
            # Initialize agent and create run
            run_id = await self._start_run()
            
            # Fetch account data once (reused by both agents)
            account_data = await self._fetch_account_data(self.agent_id)

            # Fetch recent activity for context
            recent_activity = await self._fetch_recent_activity(self.agent_id)

            # Build context inline (no separate function needed)
            ctx = RunContext(
                run_id=run_id,
                agent_id=self.agent_id,
                agent_name=self.name,
                agent_style=self.agent_style,
                model_name=self.model_name,
                research_start_time=research_start_time,
                tracker=ToolTracker(run_id),
                balance=account_data.balance,
                holdings=account_data.holdings,
                recent_activity=recent_activity,
            )

            # === RESEARCH PHASE ===
            research_result = await self._run_market_analyst(
                ctx=ctx,
                mcp_pool=mcp_pool,
            )
            ctx.research_response = research_result.research_response
            ctx.research_candidates = research_result.candidates
            ctx.research_sources = research_result.sources
            ctx.research_notes = research_result.notes
            ctx.research_tool_calls = research_result.tool_calls

            # === DECISION PHASE ===
            decision_result = await self._run_decision_maker(
                ctx=ctx,
                mcp_pool=mcp_pool,
                force_trade=force_trade,
            )
            ctx.decision = decision_result.decision
            ctx.decision_start_time = decision_result.decision_start_time
            ctx.decision_tool_calls = decision_result.tool_calls

            # Build decision sources - track what data informed the decision
            ctx.decision_sources = [
                # Research sources passed to decision maker
                *[SourceDto.web(title=s.title, url=s.url) for s in ctx.research_response.sources],
                # Internal data accessed
                SourceDto.system_context(f"Portfolio: ${ctx.balance:,.2f}, {len(ctx.holdings)} positions"),
                SourceDto.system_context(f"Recent activity: {len(ctx.recent_activity.runs) if ctx.recent_activity else 0} runs"),
            ]

            # === EXECUTION PHASE ===
            # Only execute trade for BUY/SELL decisions, skip for HOLD
            if ctx.decision.action in (TradeDecision.BUY, TradeDecision.SELL):
                execution_result = await self._execute_trade(
                    run_id=ctx.run_id,
                    agent_id=ctx.agent_id,
                    decision=ctx.decision,
                )
                ctx.trade_id = execution_result.trade_id
                ctx.execution_status = execution_result.execution_status
                ctx.execution_error = execution_result.execution_error
            else:
                # HOLD decision - skip execution phase
                ctx.execution_status = PhaseStatus.SKIPPED

            # === FINALIZATION ===
            await self._finalize_run(ctx)

            print(
                f"✅ {self.name} completed portfolio review at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # Derive trade_count from trade_id presence (1 if executed, 0 otherwise)
            return CycleResult(
                decision=ctx.decision,
                trade_count=1 if ctx.trade_id else 0,
                run_id=ctx.run_id,
            )

        except Exception as e:
            await self._handle_cycle_error(e, ctx)
            raise

    async def _start_run(self) -> int:
        """Initialize agent and create run, transition to RESEARCHING.

        Returns:
            run_id from backend

        Raises:
            RuntimeError: If agent_id is not set or run creation fails
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

        # Create run via API (POST /api/runs)
        # create_run now throws BackendAPIError on failure
        run_id = await create_run(self.agent_id)

        # Update to RESEARCHING phase
        await update_phase(run_id, RunPhase.RESEARCHING)

        # Broadcast: RESEARCHING
        broadcast_status(
            self.agent_id, self.name, PHASE_RESEARCHING, "Researching market", 20
        )

        return run_id

    async def _fetch_account_data(self, agent_id: int) -> AccountData:
        """Fetch balance and holdings once for the cycle.

        Args:
            agent_id: Agent ID for data fetching

        Returns:
            AccountData with balance and holdings

        Raises:
            RuntimeError: If fetching fails
        """
        try:
            balance = await _get_balance_raw(agent_id)
            holdings = await _get_holdings_raw(agent_id)
            return AccountData(balance=balance, holdings=holdings)
        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch account data for agent {agent_id}: {e}"
            )

    async def _fetch_recent_activity(self, agent_id: int) -> RecentActivityResponse:
        """Fetch recent trading activity for context.

        Args:
            agent_id: Agent ID for data fetching

        Returns:
            RecentActivityResponse with 30-day activity

        Raises:
            RuntimeError: If fetching fails
        """
        # get_recent_activity throws BackendAPIError on failure
        result = await get_recent_activity(agent_id, days=30)

        logger.info(f"📊 Context prepared: {result.computed_total_runs} runs, {result.computed_total_trades} trades (30 days)")
        return result

    async def _run_market_analyst(
        self,
        ctx: RunContext,
        mcp_pool,
    ) -> ResearchResult:
        """Run Market Analyst agent for research.

        Args:
            ctx: RunContext with agent info and account data
            mcp_pool: MCP pool for creating agent

        Returns:
            ResearchResult with research findings
        """
        research_start_time = datetime.now()

        # Log portfolio access
        portfolio_data = {
            "balance": round(ctx.balance, 2),
            "holdings_count": len(ctx.holdings),
            "symbols": [h.symbol for h in ctx.holdings] if ctx.holdings else []
        }
        ctx.tracker.log_data_access("Portfolio", json.dumps(portfolio_data))

        # Create Market Analyst using async factory pattern
        market_analyst = await MarketAnalyst.create(
            agent_name=ctx.agent_name,
            mcp_pool=mcp_pool,
            model_name=ctx.model_name,
        )

        # Build typed context (class converts to strings internally)
        research_context = MarketAnalystContext(
            agent_name=ctx.agent_name,
            agent_style=ctx.agent_style,
            balance=ctx.balance,
            holdings=ctx.holdings,
            recent_activity=ctx.recent_activity,
            max_positions=10,
        )

        # Build prompt using OO interface
        research_prompt = market_analyst.build_prompt(research_context)

        logger.info(f"🔬 Running Market Analyst for {ctx.agent_name}...")

        # Run Market Analyst
        result = await Runner.run(market_analyst.agent, research_prompt, max_turns=30)

        # Extract ResearchResponse - type-safe using SDK's final_output_as()
        try:
            research_response = result.final_output_as(ResearchResponse)
        except TypeError as e:
            raise RuntimeError(
                f"Market Analyst for {ctx.agent_name} failed to produce ResearchResponse: {e}"
            ) from e

        # Build sources list
        sources = [
            SourceDto.web(title=source.title, url=source.url)
            for source in research_response.sources
        ]
        # Add system context source for portfolio
        sources.append(SourceDto.system_context(f"Portfolio context: {json.dumps(portfolio_data)}"))
        sources.append(SourceDto.system_context("Retrieved 30-day trading activity history"))

        # Calculate research latency
        research_latency_ms = int(
            (datetime.now() - research_start_time).total_seconds() * 1000
        )
        logger.info(f"📊 Market Analyst completed in {research_latency_ms}ms")

        # Extract tool calls from SDK result
        parsed_calls = extract_tool_calls(result.new_items)
        tool_calls = [
            ToolCallDto(
                tool=pc.name,
                params=pc.params,
                durationMs=None,  # SDK doesn't provide individual durations
                error=pc.is_error if pc.is_error else None,
                errorMessage=pc.error_message,
            )
            for pc in parsed_calls
        ]
        logger.info(f"🔧 Market Analyst made {len(tool_calls)} tool calls")

        candidates = research_response.candidates
        logger.info(f"✅ Market Analyst found {len(candidates)} candidates with {len(sources)} sources")

        return ResearchResult(
            research_response=research_response,
            candidates=candidates,
            sources=sources,
            notes=research_response.summary,
            tool_calls=tool_calls,
        )

    async def _run_decision_maker(
        self,
        ctx: RunContext,
        mcp_pool,
        force_trade: bool,
    ) -> DecisionResult:
        """Run Decision Maker agent for trading decision.

        Args:
            ctx: RunContext with research results and account data
            mcp_pool: MCP pool for creating agent
            force_trade: If True, agent must make BUY/SELL (no HOLD)

        Returns:
            DecisionResult with decision and timing
        """
        # Update to DECIDING phase
        await update_phase(ctx.run_id, RunPhase.DECIDING)
        decision_start_time = datetime.now()

        # Broadcast: DECIDING
        broadcast_status(
            ctx.agent_id, ctx.agent_name, PHASE_DECIDING, "Making investment decision", 70
        )

        # Create Decision Maker using async factory pattern
        decision_maker = await DecisionMaker.create(
            agent_name=ctx.agent_name,
            agent_id=ctx.agent_id,
            mcp_pool=mcp_pool,
            model_name=ctx.model_name,
        )

        # Type narrowing: research_response is guaranteed set by _run_market_analyst
        assert ctx.research_response is not None, "research_response must be set before decision phase"

        # Build typed context (class converts to strings internally)
        decision_context = DecisionContext(
            agent_name=ctx.agent_name,
            agent_style=ctx.agent_style,
            research_response=ctx.research_response,
            balance=ctx.balance,
            holdings=ctx.holdings,
            recent_activity=ctx.recent_activity,
            force_trade=force_trade,
            max_positions=10,
        )

        # Build prompt using OO interface
        decision_prompt = decision_maker.build_prompt(decision_context)

        logger.info(f"🧠 Running Decision Maker for {ctx.agent_name}...")

        # Run Decision Maker agent - get structured output directly
        result = await Runner.run(decision_maker.agent, decision_prompt, max_turns=30)

        # Extract TradingDecision - type-safe using SDK's final_output_as()
        try:
            decision = result.final_output_as(TradingDecision)
        except TypeError as e:
            raise RuntimeError(
                f"Decision Maker for {ctx.agent_name} failed to produce TradingDecision: {e}"
            ) from e

        logger.info(f"✅ Decision Maker: {decision.action} {decision.symbol or ''}")

        # Extract tool calls from SDK result
        parsed_calls = extract_tool_calls(result.new_items)
        tool_calls = [
            ToolCallDto(
                tool=pc.name,
                params=pc.params,
                durationMs=None,  # SDK doesn't provide individual durations
                error=pc.is_error if pc.is_error else None,
                errorMessage=pc.error_message,
            )
            for pc in parsed_calls
        ]
        logger.info(f"🔧 Decision Maker made {len(tool_calls)} tool calls")

        # Calculate decision latency
        decision_latency_ms = int(
            (datetime.now() - decision_start_time).total_seconds() * 1000
        )
        logger.info(f"📊 Decision Maker completed in {decision_latency_ms}ms")

        return DecisionResult(
            decision=decision,
            decision_start_time=decision_start_time,
            tool_calls=tool_calls,
        )

    async def _execute_trade(
        self,
        run_id: int,
        agent_id: int,
        decision: Optional[TradingDecision],
    ) -> ExecutionResult:
        """Execute BUY/SELL/HOLD decision.

        Args:
            run_id: Run ID for tracking
            agent_id: Agent ID for trading
            decision: Trading decision to execute

        Returns:
            ExecutionResult with execution results
        """
        # Validate we have a decision
        if not decision:
            raise RuntimeError(
                f"Agent {agent_id} reached execution phase but no decision was recorded. "
                "Decision Maker agent should have called decide_action tool."
            )

        logger.info(f"✅ Validated decision: {decision.action} {decision.symbol or ''}")
        logger.info(f"🟡 ABOUT TO EXECUTE: decision={decision}")

        trade_id = None
        execution_status = None
        execution_error = None

        if decision.action in (TradeDecision.BUY, TradeDecision.SELL):
            action = decision.action
            symbol = decision.symbol
            quantity = decision.quantity

            logger.info(f"🟢 EXECUTING: {action} {quantity} shares of {symbol}")

            # Update to TRADING phase
            await update_phase(run_id, RunPhase.TRADING)

            # Broadcast: TRADING
            broadcast_status(
                agent_id, self.name, PHASE_TRADING, "Executing trade", 90
            )

            try:
                if action == TradeDecision.BUY:
                    result = await buy_shares(
                        agent_id,
                        symbol,
                        quantity,
                        runId=run_id,
                        agent_name=self.name,
                    )
                else:
                    result = await sell_shares(
                        agent_id,
                        symbol,
                        quantity,
                        runId=run_id,
                        agent_name=self.name,
                    )

                execution_status = PhaseStatus.COMPLETED
                trade_id = result.tradeId

            except Exception as trade_err:
                logger.error(f"Trade execution failed: {trade_err}")
                execution_status = PhaseStatus.FAILED
                execution_error = str(trade_err)
        else:
            # HOLD decision - no trade execution
            execution_status = PhaseStatus.SKIPPED

        return ExecutionResult(
            execution_status=execution_status,
            trade_id=trade_id,
            execution_error=execution_error,
        )

    async def _finalize_run(self, ctx: RunContext) -> None:
        """Complete run with all data.

        Args:
            ctx: RunContext with all data to persist

        Preconditions (enforced via assertions):
            - decision_start_time: set before decision phase
            - decision: set by _run_decision_maker
            - research_response: set by _run_market_analyst
        """
        # Fail-fast assertions - document and enforce preconditions
        assert ctx.decision_start_time is not None, "decision_start_time must be set"
        assert ctx.decision is not None, "decision must be set"
        assert ctx.research_response is not None, "research_response must be set"

        # Calculate latencies
        decision_latency_ms = int(
            (datetime.now() - ctx.decision_start_time).total_seconds() * 1000
        )
        research_latency_ms = int(
            (ctx.decision_start_time - ctx.research_start_time).total_seconds() * 1000
        )

        # Extract decision details (decision guaranteed by _run_decision_maker fail-fast)
        decision = ctx.decision
        trade_decision = decision.action
        symbol = decision.symbol if decision.action in (TradeDecision.BUY, TradeDecision.SELL) else None
        quantity = decision.quantity if decision.action in (TradeDecision.BUY, TradeDecision.SELL) else None

        # Build reasoning DTO from decision's structured fields
        # Use new structured fields if available, fall back to fullReasoning for legacy
        reasoning = ReasoningDto(
            portfolioContext=decision.portfolioContext[:2000] if decision.portfolioContext else None,
            historicalContext=decision.historicalContext[:2000] if decision.historicalContext else None,
            researchSummary=decision.researchSummary[:2000] if decision.researchSummary else None,
            candidateEvaluation=decision.candidateEvaluation[:2000] if decision.candidateEvaluation else None,
            finalRationale=(decision.finalRationale or decision.fullReasoning)[:2000] or None,
        )

        # Monitor LLM structured reasoning field population
        reasoning_fields = {
            "portfolioContext": reasoning.portfolioContext,
            "historicalContext": reasoning.historicalContext,
            "researchSummary": reasoning.researchSummary,
            "candidateEvaluation": reasoning.candidateEvaluation,
            "finalRationale": reasoning.finalRationale,
        }
        populated = [k for k, v in reasoning_fields.items() if v]
        empty = [k for k, v in reasoning_fields.items() if not v]
        logger.info(
            f"📝 Reasoning fields populated: {', '.join(populated) or 'NONE'} "
            f"(empty: {', '.join(empty) or 'none'})"
        )

        # Build nested phase DTOs
        research_data = ResearchPhaseData(
            candidates=ctx.research_candidates,
            sources=ctx.research_sources,
            notes=ctx.research_notes,
            toolCalls=ctx.research_tool_calls,
            latencyMs=research_latency_ms,
        )

        decision_data = DecisionPhaseData(
            decision=trade_decision,
            symbol=symbol,
            quantity=quantity,
            reasoning=reasoning,
            sources=ctx.decision_sources,
            toolCalls=ctx.decision_tool_calls,
            latencyMs=decision_latency_ms,
        )

        execution_data = ExecutionPhaseData(
            tradeId=ctx.trade_id,
            status=ctx.execution_status,
            errorDetails=ctx.execution_error,
        )

        # Build CompleteRunData with nested structure
        complete_data = CompleteRunData(
            research=research_data,
            decision=decision_data,
            execution=execution_data,
        )

        # Complete the run via API
        await complete_run(ctx.run_id, complete_data)

        # Broadcast: COMPLETED
        outcome_message = (
            "Completed - 1 trade executed"
            if ctx.trade_id
            else "Completed - No trades (HOLD decision)"
        )
        broadcast_status(
            ctx.agent_id,
            ctx.agent_name,
            PHASE_COMPLETED,
            outcome_message,
            100,
            outcome=outcome_message,
        )

    async def _handle_cycle_error(self, error: Exception, ctx: Optional[RunContext]) -> None:
        """Handle cycle execution error.

        Args:
            error: Exception that occurred
            ctx: RunContext if available (may be None if Phase 1 failed)
        """
        agent_id = ctx.agent_id if ctx else self.agent_id
        agent_name = ctx.agent_name if ctx else self.name
        run_id = ctx.run_id if ctx else None

        # Broadcast: ERROR
        broadcast_status(
            agent_id,
            agent_name,
            PHASE_ERROR,
            f"Error: {str(error)}",
            0,
            outcome=f"Failed: {str(error)}",
        )

        # Update run to ERROR phase and complete with error details
        if run_id is not None:
            await update_phase(run_id, RunPhase.ERROR)

            # Complete with partial data and error (nested structure)
            error_decision = DecisionPhaseData(
                decision=TradeDecision.HOLD,
            )
            error_execution = ExecutionPhaseData(
                status=PhaseStatus.FAILED,
                errorDetails=str(error)[:500],
            )
            error_data = CompleteRunData(
                decision=error_decision,
                execution=error_execution,
            )
            await complete_run(run_id, error_data)

