"""Agent execution orchestration.

`AgentExecutor.execute_cycle` is the top-level entry point for one trading
cycle. It:

- fetches account balance, holdings, and recent activity via BackendClient
- assembles a `RunContext` carrying all per-cycle state
- constructs a single `RunLifecycle` and threads it through four phase
  modules: research → decision → execution → finalization
- routes failures through `lifecycle.fail` (best-effort error recording)
  before re-raising the original exception

Sequential operations with explicit parameters and typed results; no silent
fallbacks.
"""

import logging
from datetime import datetime

from backend.client import get_backend_client
from backend.run_lifecycle import RunLifecycle
from config import config
from infra.pricing import _UNKNOWN_MODELS_WARNED, MODEL_PRICING  # noqa: F401
from infra.telemetry import extract_run_telemetry, extract_usage_metrics  # noqa: F401
from models import CycleResult, InvestmentStyle
from models.api_responses import RecentActivityResponse
from models.orchestration import (
    AccountData,
    ExecutionResult,
    RunContext,
)
from models.run_tracking import (
    PhaseStatus,
    SourceDto,
    TradeDecision,
)
from tools.trading_tools import _get_account_report_raw

logger = logging.getLogger(__name__)

RESEARCH_MAX_ATTEMPTS = 3
AGENT_MAX_TURNS = 30
MAX_POSITIONS = 10

RECENT_ACTIVITY_LOOKBACK_DAYS = 30

MAX_REASONING_FIELD_LEN = 2000
MAX_ERROR_MESSAGE_LEN = 500

# Imported after the module-level constants so phases.* can
# `from agent_executor import MAX_POSITIONS, ...` without circular import.
from phases.decision_phase import run_decision_phase  # noqa: E402
from phases.execution_phase import run_execution_phase  # noqa: E402
from phases.finalization import run_finalization_phase  # noqa: E402
from phases.research_phase import run_research_phase  # noqa: E402


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

        # Constructed outside the try: so it's in scope for the except handler.
        # RunLifecycle.__init__ does no I/O; lifecycle.start() below is what can raise.
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
                *[
                    SourceDto.web(title=s.title, url=s.url)
                    for s in ctx.research.research_response.webSources
                ],
                # Internal data accessed
                SourceDto.system_context(
                    f"Portfolio: ${ctx.balance:,.2f}, {len(ctx.holdings)} positions"
                ),
                SourceDto.system_context(
                    f"Recent activity: {len(ctx.recent_activity.runs) if ctx.recent_activity else 0} runs"
                ),
            ]

            # === EXECUTION PHASE ===
            # Only execute trade for BUY/SELL decisions, skip for HOLD
            if ctx.decision_result.decision.action in (TradeDecision.BUY, TradeDecision.SELL):
                ctx.execution_result = await run_execution_phase(
                    run_id=ctx.run_id,
                    agent_id=ctx.agent_id,
                    agent_name=self.name,
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
            await run_finalization_phase(ctx, lifecycle)

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

        logger.info(
            f"📊 Context prepared: {result.computed_total_runs} runs, {result.computed_total_trades} trades (30 days)"
        )
        return result

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
