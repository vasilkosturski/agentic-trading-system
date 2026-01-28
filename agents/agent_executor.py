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
from typing import List, Optional

from agents import Runner

from models import TradingDecision, ResearchResponse, CycleResult, Holding
from models.orchestration import (
    RunContext,
    ResearchResult,
    DecisionResult,
    ExecutionResult,
)
from models.api_responses import RecentActivityResponse, ToolError
from models.run_tracking import (
    CompleteRunData,
    PhaseStatus,
    ReasoningDto,
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

# Import two-agent architecture
from market_analyst import create_market_analyst_agent, build_research_prompt
from decision_maker import create_decision_maker_agent, build_decision_prompt

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
            balance, holdings = await self._fetch_account_data(self.agent_id)
            
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
                balance=balance,
                holdings=holdings,
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

            # === DECISION PHASE ===
            decision_result = await self._run_decision_maker(
                ctx=ctx,
                mcp_pool=mcp_pool,
                force_trade=force_trade,
            )
            ctx.decision = decision_result.decision
            ctx.decision_start_time = decision_result.decision_start_time

            # === EXECUTION PHASE ===
            execution_result = await self._execute_trade(
                run_id=ctx.run_id,
                agent_id=ctx.agent_id,
                decision=ctx.decision,
            )
            ctx.trade_id = execution_result.trade_id
            ctx.trade_count = execution_result.trade_count
            ctx.execution_status = execution_result.execution_status
            ctx.execution_error = execution_result.execution_error

            # === FINALIZATION ===
            await self._finalize_run(ctx)

            print(
                f"✅ {self.name} completed portfolio review at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            return CycleResult(
                decision=ctx.decision,
                trade_count=ctx.trade_count,
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
        run_id = await create_run(self.agent_id)
        if run_id is None:
            raise RuntimeError(
                f"Failed to create run for {self.name}. Cannot proceed without runId."
            )

        # Update to RESEARCHING phase
        await update_phase(run_id, RunPhase.RESEARCHING)

        # Broadcast: RESEARCHING
        broadcast_status(
            self.agent_id, self.name, PHASE_RESEARCHING, "Researching market", 20
        )

        return run_id

    async def _fetch_account_data(self, agent_id: int) -> tuple[float, List[Holding]]:
        """Fetch balance and holdings once for the cycle.

        Args:
            agent_id: Agent ID for data fetching

        Returns:
            Tuple of (balance, holdings)
        """
        balance = await _get_balance_raw(agent_id)
        holdings = await _get_holdings_raw(agent_id)
        return balance, holdings

    async def _fetch_recent_activity(self, agent_id: int) -> RecentActivityResponse:
        """Fetch recent trading activity for context.

        Args:
            agent_id: Agent ID for data fetching

        Returns:
            RecentActivityResponse with 30-day activity

        Raises:
            RuntimeError: If fetching fails
        """
        result = await get_recent_activity(agent_id, days=30)

        if isinstance(result, ToolError):
            raise RuntimeError(
                f"Failed to fetch recent activity for agent {agent_id}: {result.error}"
            )

        logger.info(f"📊 Context prepared: {result.totalRuns} runs, {result.totalTrades} trades (30 days)")
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

        # Build holdings summary as JSON list
        holdings_summary = json.dumps([h.symbol for h in ctx.holdings]) if ctx.holdings else "[]"

        # Log portfolio access
        portfolio_data = {
            "balance": round(ctx.balance, 2),
            "holdings_count": len(ctx.holdings),
            "symbols": [h.symbol for h in ctx.holdings] if ctx.holdings else []
        }
        ctx.tracker.log_data_access("Portfolio", json.dumps(portfolio_data))

        # Create Market Analyst agent
        analyst = await create_market_analyst_agent(
            agent_name=ctx.agent_name,
            mcp_pool=mcp_pool,
            model_name=ctx.model_name,
        )

        # Build research prompt (serialize recent_activity to JSON for LLM)
        research_prompt = build_research_prompt(
            agent_name=ctx.agent_name,
            agent_style=ctx.agent_style,
            balance=ctx.balance,
            position_count=len(ctx.holdings),
            max_positions=10,
            holdings_summary=holdings_summary,
            historical_context=ctx.recent_activity.model_dump_json(),
            force_trade=False,
        )

        logger.info(f"🔬 Running Market Analyst for {ctx.agent_name}...")

        # Run Market Analyst
        result = await Runner.run(analyst, research_prompt, max_turns=30)

        # Extract ResearchResponse - FAIL FAST if no output
        if not hasattr(result, 'output') or not result.output:
            raise RuntimeError(
                f"Market Analyst for {ctx.agent_name} failed to produce structured output. "
                f"Result type: {type(result)}, has output attr: {hasattr(result, 'output')}"
            )
        research_response = result.output

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

        candidates = research_response.candidates if hasattr(research_response, 'candidates') else []
        logger.info(f"✅ Market Analyst found {len(candidates)} candidates with {len(sources)} sources")

        return ResearchResult(
            research_response=research_response,
            candidates=candidates,
            sources=sources,
            notes=research_response.summary,
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

        # Build holdings summary as JSON list (reuse from context)
        holdings_summary = json.dumps([h.symbol for h in ctx.holdings]) if ctx.holdings else "[]"

        # Create Decision Maker agent (now uses structured output)
        trader = await create_decision_maker_agent(
            agent_name=ctx.agent_name,
            agent_id=ctx.agent_id,
            mcp_pool=mcp_pool,
            model_name=ctx.model_name,
        )

        # Build decision prompt (serialize recent_activity to JSON for LLM)
        decision_prompt = build_decision_prompt(
            agent_name=ctx.agent_name,
            agent_style=ctx.agent_style,
            research_response=ctx.research_response,
            balance=ctx.balance,
            position_count=len(ctx.holdings),
            max_positions=10,
            holdings_summary=holdings_summary,
            historical_context=ctx.recent_activity.model_dump_json(),
            force_trade=force_trade,
        )

        logger.info(f"🧠 Running Decision Maker for {ctx.agent_name}...")

        # Run Decision Maker agent - get structured output directly
        result = await Runner.run(trader, decision_prompt, max_turns=30)

        # Extract TradingDecision from structured output - FAIL FAST if no output
        if not hasattr(result, 'output') or not result.output:
            raise RuntimeError(
                f"Decision Maker for {ctx.agent_name} failed to produce structured output. "
                f"Result type: {type(result)}, has output attr: {hasattr(result, 'output')}"
            )

        decision = result.output

        logger.info(f"✅ Decision Maker: {decision.action} {decision.symbol or ''}")

        # Calculate decision latency
        decision_latency_ms = int(
            (datetime.now() - decision_start_time).total_seconds() * 1000
        )
        logger.info(f"📊 Decision Maker completed in {decision_latency_ms}ms")

        return DecisionResult(
            decision=decision,
            decision_start_time=decision_start_time,
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
        trade_count = 0
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

                trade_count = 1
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
            trade_id=trade_id,
            trade_count=trade_count,
            execution_status=execution_status,
            execution_error=execution_error,
        )

    async def _finalize_run(self, ctx: RunContext) -> None:
        """Complete run with all data.

        Args:
            ctx: RunContext with all data to persist
        """
        # Calculate latencies
        decision_latency_ms = None
        research_latency_ms = None
        
        if ctx.decision_start_time:
            decision_latency_ms = int(
                (datetime.now() - ctx.decision_start_time).total_seconds() * 1000
            )
        
        if ctx.research_start_time and ctx.decision_start_time:
            research_latency_ms = int(
                (ctx.decision_start_time - ctx.research_start_time).total_seconds() * 1000
            )

        # Determine trade decision
        trade_decision = TradeDecision.HOLD
        symbol = None
        quantity = None

        if ctx.decision:
            if ctx.decision.action == TradeDecision.BUY:
                trade_decision = TradeDecision.BUY
            elif ctx.decision.action == TradeDecision.SELL:
                trade_decision = TradeDecision.SELL
            symbol = ctx.decision.symbol if ctx.decision.action in (TradeDecision.BUY, TradeDecision.SELL) else None
            quantity = ctx.decision.quantity if ctx.decision.action in (TradeDecision.BUY, TradeDecision.SELL) else None

        # Build reasoning DTO from decision
        reasoning = None
        if ctx.decision and ctx.decision.fullReasoning:
            reasoning = ReasoningDto(
                portfolioContext=None,
                historicalContext=None,
                researchSummary=None,
                candidateEvaluation=None,
                finalRationale=ctx.decision.fullReasoning[:2000]
            )

        # Build CompleteRunData
        complete_data = CompleteRunData(
            # Research phase
            candidates=ctx.research_candidates,
            researchSources=ctx.research_sources,
            researchNotes=ctx.research_notes,
            researchToolCalls=ctx.research_tool_calls,
            researchLatencyMs=research_latency_ms,
            # Decision phase
            decision=trade_decision,
            symbol=symbol,
            quantity=quantity,
            reasoning=reasoning,
            decisionLatencyMs=decision_latency_ms,
            # Execution phase
            tradeId=ctx.trade_id,
            executionStatus=ctx.execution_status,
            errorDetails=ctx.execution_error,
        )

        # Complete the run via API
        await complete_run(ctx.run_id, complete_data)

        # Broadcast: COMPLETED
        outcome_message = (
            f"Completed - {ctx.trade_count} trade(s) executed"
            if ctx.trade_count > 0
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

            # Complete with partial data and error
            error_data = CompleteRunData(
                decision=TradeDecision.HOLD,
                executionStatus=PhaseStatus.FAILED,
                errorDetails=str(error)[:500],
            )
            await complete_run(run_id, error_data)

