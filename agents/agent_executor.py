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

import logging
from datetime import datetime

from config import config
# Re-exported so existing references via ``agent_executor._UNKNOWN_MODELS_WARNED``
# (e.g. legacy test fixtures) continue to resolve. Telemetry helpers below
# import these directly from ``pricing``.
from pricing import MODEL_PRICING, _UNKNOWN_MODELS_WARNED  # noqa: F401
from telemetry import extract_usage_metrics, extract_run_telemetry  # noqa: F401
from run_lifecycle import RunLifecycle

from models import TradingDecision, CycleResult, InvestmentStyle
from models.orchestration import (
    AccountData,
    RunContext,
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
    SourceDto,
    TradeDecision,
)
# Import direct function tools.
from trading_tools import (
    buy_shares,
    sell_shares,
    _get_account_report_raw,
)
from backend_client import get_backend_client

# Two-agent architecture imports lived here until Tasks 6 and 7 of the
# decomposition plan lifted them into phase modules. ``MarketAnalyst`` now
# lives behind ``phases.research_phase.run_research_phase``; ``DecisionMaker``
# now lives behind ``phases.decision_phase.run_decision_phase``.

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------
# Grouped by domain. Untyped int literals match the project convention from
# `decision_maker.py:51` (`DEFAULT_POSITION_SIZING_PCT = 15`).

# Agent run limits
RESEARCH_MAX_ATTEMPTS = 3
AGENT_MAX_TURNS = 30
MAX_POSITIONS = 10

# Data fetch limits
RECENT_ACTIVITY_LOOKBACK_DAYS = 30

# String truncation limits
MAX_REASONING_FIELD_LEN = 2000
MAX_ERROR_MESSAGE_LEN = 500

# Pricing constants live in pricing.py (extracted in refactor Task 1) and
# telemetry helpers (extract_usage_metrics + extract_run_telemetry) live in
# telemetry.py (extracted in refactor Task 2). Both modules' symbols are
# re-exported via the ``from pricing import ...`` / ``from telemetry import
# ...`` statements at the top of this module so existing references like
# ``agent_executor.MODEL_PRICING`` or
# ``agent_executor._UNKNOWN_MODELS_WARNED`` continue to resolve.

# Phase-module imports (extracted in Task 6+ of the decomposition plan).
# These imports are placed AFTER the module-constants block above so that
# phases.research_phase can `from agent_executor import MAX_POSITIONS, ...`
# without triggering a circular import — by the time Python begins
# initializing phases.research_phase, the names it needs are already bound
# on this module.
from phases.research_phase import run_research_phase  # noqa: E402
from phases.decision_phase import run_decision_phase  # noqa: E402


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

    Concurrency: single cycle per executor instance at a time. Do not call
    execute_cycle concurrently on the same instance. The orchestrator
    pattern in trading_system.py creates one AgentExecutor per agent and
    fans out via asyncio.gather — that is the supported parallelism model.
    """

    def __init__(
        self,
        agent_id: int,
        name: str,
        agent_style: InvestmentStyle,
        model_name: str | None = None,
    ):
        """Initialize executor with agent identity.

        Args:
            agent_id: Unique agent identifier
            name: Agent name (e.g., "Warren")
            agent_style: Investment style enum value
            model_name: OpenAI model name to use for agents. Defaults to config.OPENAI_MODEL.
        """
        if model_name is None:
            model_name = config.OPENAI_MODEL
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
        ctx: RunContext | None = None

        logger.info(
            f"🤖 {self.name} starting portfolio review at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Construct lifecycle BEFORE the try: block so it's in scope for the
        # except: handler that calls _handle_cycle_error. RunLifecycle() is a
        # pure dataclass-style instantiation and can't raise — the only
        # outbound I/O is in lifecycle.start() below.
        lifecycle = RunLifecycle(self.agent_id, self.name)

        try:
            # === INITIALIZATION ===
            # Set timing at orchestrator level (not buried in helper)
            research_start_time = datetime.now()

            run_id = await lifecycle.start()
            
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
                balance=account_data.balance,
                holdings=account_data.holdings,
                recent_activity=recent_activity,
            )

            # === RESEARCH PHASE ===
            research_result = await run_research_phase(
                ctx=ctx,
                mcp_pool=mcp_pool,
            )
            ctx.research = research_result

            # === DECISION PHASE ===
            decision_result = await run_decision_phase(
                ctx=ctx,
                mcp_pool=mcp_pool,
                force_trade=force_trade,
                lifecycle=lifecycle,
            )
            ctx.decision_result = decision_result

            # Build decision sources - track what data informed the decision
            ctx.decision_sources = [
                # Research sources passed to decision maker
                *[SourceDto.web(title=s.title, url=s.url) for s in ctx.research.research_response.webSources],
                # Internal data accessed
                SourceDto.system_context(f"Portfolio: ${ctx.balance:,.2f}, {len(ctx.holdings)} positions"),
                SourceDto.system_context(f"Recent activity: {len(ctx.recent_activity.runs) if ctx.recent_activity else 0} runs"),
            ]

            # === EXECUTION PHASE ===
            # Only execute trade for BUY/SELL decisions, skip for HOLD
            if ctx.decision_result.decision.action in (TradeDecision.BUY, TradeDecision.SELL):
                ctx.execution_result = await self._execute_trade(
                    run_id=ctx.run_id,
                    agent_id=ctx.agent_id,
                    decision=ctx.decision_result.decision,
                    lifecycle=lifecycle,
                )
            else:
                # HOLD decision - skip execution phase
                ctx.execution_result = ExecutionResult(
                    execution_status=PhaseStatus.SKIPPED,
                    trade_id=None,
                    execution_error=None,
                )

            # === FINALIZATION ===
            await self._finalize_run(ctx, lifecycle)

            logger.info(
                f"✅ {self.name} completed portfolio review at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # Derive trade_count from trade_id presence (1 if executed, 0 otherwise)
            return CycleResult(
                decision=ctx.decision_result.decision,
                trade_count=1 if ctx.execution_result.trade_id else 0,
                run_id=ctx.run_id,
            )

        except Exception as e:
            await self._handle_cycle_error(e, ctx, lifecycle)
            raise

    async def _start_run(self) -> int:
        """Initialize agent and create run, transition to RESEARCHING.

        Thin wrapper around `RunLifecycle.start()` — preserved for the
        existing `TestAgentExecutorStartRun` tests that call
        `executor._start_run()` directly. `execute_cycle` no longer
        invokes this method; it constructs its own `RunLifecycle` and
        calls `lifecycle.start()` directly so the same lifecycle
        instance can drive the remaining transitions (Task 5+).

        Scheduled for deletion in Task 10 of the decomposition plan.

        Returns:
            run_id from backend

        Raises:
            RuntimeError: If agent_id is not set
            BackendAPIError: If create_run or update_phase fails
        """
        lifecycle = RunLifecycle(self.agent_id, self.name)
        return await lifecycle.start()

    async def _fetch_account_data(self, agent_id: int) -> AccountData:
        """Fetch balance and holdings once for the cycle.

        Uses a single HTTP call to the account report endpoint to get both
        balance and holdings, avoiding duplicate requests.

        Args:
            agent_id: Agent ID for data fetching

        Returns:
            AccountData with balance and holdings

        Raises:
            BackendAPIError: If the backend request fails.
        """
        # _get_account_report_raw throws BackendAPIError on failure
        report = await _get_account_report_raw(agent_id)
        return AccountData(balance=report.balance, holdings=report.holdings)

    async def _fetch_recent_activity(self, agent_id: int) -> RecentActivityResponse:
        """Fetch recent trading activity for context.

        Args:
            agent_id: Agent ID for data fetching

        Returns:
            RecentActivityResponse with 30-day activity

        Raises:
            RuntimeError: If fetching fails
        """
        # BackendClient.get_recent_activity throws BackendAPIError on failure
        client = get_backend_client()
        result = await client.get_recent_activity(agent_id, days=RECENT_ACTIVITY_LOOKBACK_DAYS)

        logger.info(f"📊 Context prepared: {result.computed_total_runs} runs, {result.computed_total_trades} trades (30 days)")
        return result

    async def _execute_trade(
        self,
        run_id: int,
        agent_id: int,
        decision: TradingDecision,
        lifecycle: RunLifecycle,
    ) -> ExecutionResult:
        """Execute BUY/SELL decision. HOLD is filtered by caller in execute_cycle.

        Args:
            run_id: Run ID for tracking
            agent_id: Agent ID for trading
            decision: Trading decision to execute (must be BUY or SELL)

        Returns:
            ExecutionResult with execution results
        """
        action = decision.action
        symbol = decision.symbol
        quantity = decision.quantity

        logger.info(f"✅ Validated decision: {action} {symbol or ''}")
        logger.info(f"🟡 ABOUT TO EXECUTE: decision={decision}")
        logger.info(f"🟢 EXECUTING: {action} {quantity} shares of {symbol}")

        await lifecycle.transition_to_trading(run_id)

        trade_id = None
        execution_status: PhaseStatus
        execution_error: str | None = None

        try:
            if action == TradeDecision.BUY:
                result = await buy_shares(
                    agent_id,
                    symbol,
                    quantity,
                    runId=run_id,
                    agent_name=self.name,
                )
            else:  # SELL
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

        return ExecutionResult(
            execution_status=execution_status,
            trade_id=trade_id,
            execution_error=execution_error,
        )

    async def _finalize_run(self, ctx: RunContext, lifecycle: RunLifecycle) -> None:
        """Complete run with all data.

        Args:
            ctx: RunContext with all data to persist
            lifecycle: RunLifecycle instance driving phase transitions

        Preconditions (enforced via assertions):
            - research: set by _run_market_analyst
            - decision_result: set by _run_decision_maker
            - execution_result: set by execute_cycle (BUY/SELL branch or HOLD short-circuit)
        """
        # Fail-fast assertions - document and enforce preconditions
        assert ctx.research is not None, "research must be set"
        assert ctx.decision_result is not None, "decision_result must be set"
        assert ctx.execution_result is not None, "execution_result must be set"

        # Calculate latencies — research_latency_ms is single-source-of-truth
        # on ResearchResult (set by _run_market_analyst from its own wall clock),
        # avoiding drift vs the previous recompute that subtracted research_start
        # from decision_start (which omits time spent in _run_decision_maker setup).
        decision_latency_ms = int(
            (datetime.now() - ctx.decision_result.decision_start_time).total_seconds() * 1000
        )
        research_latency_ms = ctx.research.research_latency_ms

        # Extract decision details (decision_result guaranteed by _run_decision_maker fail-fast)
        decision = ctx.decision_result.decision
        trade_decision = TradeDecision(decision.action.value)
        symbol = decision.symbol if decision.action in (TradeDecision.BUY, TradeDecision.SELL) else None
        quantity = decision.quantity if decision.action in (TradeDecision.BUY, TradeDecision.SELL) else None

        # Build reasoning DTO with direct 1:1 field mapping from TradingDecision.
        reasoning = ReasoningDto(
            rationale=decision.rationale[:MAX_REASONING_FIELD_LEN] if decision.rationale else None,
            portfolioContext=decision.portfolioContext[:MAX_REASONING_FIELD_LEN] if decision.portfolioContext else None,
            historicalContext=decision.historicalContext[:MAX_REASONING_FIELD_LEN] if decision.historicalContext else None,
            researchContext=decision.researchContext[:MAX_REASONING_FIELD_LEN] if decision.researchContext else None,
        )

        logger.info(
            f"📝 Reasoning: mapped 4 fields (rationale, portfolioContext, historicalContext, researchContext)"
        )

        # Build nested phase DTOs
        research_data = ResearchPhaseData(
            candidates=ctx.research.candidates,
            sources=ctx.research.sources,
            notes=ctx.research.notes,
            toolCalls=ctx.research.tool_calls,
            latencyMs=research_latency_ms,
            metrics=ctx.research.usage_metrics,
            systemPrompt=ctx.market_analyst_system_prompt,
            taskPrompt=ctx.market_analyst_task_prompt,
        )

        decision_data = DecisionPhaseData(
            decision=trade_decision,
            symbol=symbol,
            quantity=quantity,
            reasoning=reasoning,
            sources=ctx.decision_sources,
            toolCalls=ctx.decision_result.tool_calls,
            latencyMs=decision_latency_ms,
            metrics=ctx.decision_result.usage_metrics,
            systemPrompt=ctx.decision_maker_system_prompt,
            taskPrompt=ctx.decision_maker_task_prompt,
        )

        execution_data = ExecutionPhaseData(
            tradeId=ctx.execution_result.trade_id,
            status=ctx.execution_result.execution_status,
            errorDetails=ctx.execution_result.execution_error,
        )

        # Build CompleteRunData with nested structure
        complete_data = CompleteRunData(
            research=research_data,
            decision=decision_data,
            execution=execution_data,
        )

        # outcome_message branches on execution_status so a FAILED BUY/SELL
        # isn't mislabeled as 'No trades (HOLD decision)' (the prior
        # implementation branched on trade_id truthiness, which collapsed
        # FAILED and SKIPPED into the same message).
        status = ctx.execution_result.execution_status
        if status == PhaseStatus.COMPLETED:
            outcome_message = "Completed - 1 trade executed"
        elif status == PhaseStatus.SKIPPED:
            outcome_message = "Completed - No trades (HOLD decision)"
        elif status == PhaseStatus.FAILED:
            outcome_message = "Completed - Trade attempted but failed"
        else:
            outcome_message = f"Completed - Unknown status: {status}"

        await lifecycle.complete(ctx.run_id, complete_data, outcome_message)

    async def _handle_cycle_error(
        self,
        error: Exception,
        ctx: RunContext | None,
        lifecycle: RunLifecycle,
    ) -> None:
        """Handle cycle execution error.

        Best-effort error recording — never masks the original exception.

        Args:
            error: Exception that occurred
            ctx: RunContext if available (may be None if Phase 1 failed)
            lifecycle: RunLifecycle instance to delegate failure recording to
        """
        run_id = ctx.run_id if ctx else None
        await lifecycle.fail(run_id, error)

