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

from agents import Runner, Usage, RunResult

from config import config
from guardrail_retry import run_with_guardrail_retry
from pricing import MODEL_PRICING, _UNKNOWN_MODELS_WARNED

from models import TradingDecision, ResearchResponse, CycleResult, InvestmentStyle
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
from models.usage_metrics import UsageMetrics

# Import direct function tools
from trading_tools import (
    initialize_agent,
    buy_shares,
    sell_shares,
    _get_account_report_raw,
)
from backend_client import get_backend_client

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

# Import SDK parsing for tool call extraction
from utils.sdk_parser import extract_tool_calls
from models.run_tracking import ToolCallDto

# Import two-agent architecture (OO classes with typed inputs)
from market_analyst import MarketAnalyst, MarketAnalystContext
from decision_maker import DecisionMaker, DecisionContext

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

# Pricing constants live in pricing.py (extracted in refactor Task 1).
# Re-exported via the `from pricing import ...` statement at the top of
# this module, so existing references like `agent_executor.MODEL_PRICING`
# continue to resolve.


def _extract_usage_metrics(usage: Usage, model_name: str) -> UsageMetrics:
    """Extract token usage metrics from SDK RunResultBase.context_wrapper.usage.

    Args:
        usage: Usage object from result.context_wrapper.usage
        model_name: Model name passed to Agent() constructor (fallback if
            SDK doesn't provide it).

    Returns:
        UsageMetrics with token metric fields matching backend DTOs.
    """
    cached = 0
    if usage.input_tokens_details:
        cached = getattr(usage.input_tokens_details, 'cached_tokens', 0) or 0

    reasoning = 0
    if usage.output_tokens_details:
        reasoning = getattr(usage.output_tokens_details, 'reasoning_tokens', 0) or 0

    # Try SDK first, fall back to the model name we passed to Agent()
    sdk_model = None
    if usage.request_usage_entries:
        sdk_model = getattr(usage.request_usage_entries[0], 'model_name', None)

    resolved_name: str = sdk_model if sdk_model is not None else model_name

    input_tokens = usage.input_tokens or 0
    output_tokens = usage.output_tokens or 0

    pricing = MODEL_PRICING.get(resolved_name)
    cost_usd: float | None
    if pricing is None:
        if resolved_name not in _UNKNOWN_MODELS_WARNED:
            logger.warning(
                f"No pricing entry for model {resolved_name!r}; costUsd will be None. "
                f"Refresh agents/model_prices.json (see MODEL_PRICES_README.md)."
            )
            _UNKNOWN_MODELS_WARNED.add(resolved_name)
        cost_usd = None
    else:
        input_per_m, output_per_m = pricing
        cost_usd = round((input_tokens * input_per_m + output_tokens * output_per_m) / 1_000_000, 6)

    return UsageMetrics(
        tokensUsed=usage.total_tokens,
        inputTokens=input_tokens,
        outputTokens=output_tokens,
        numTurns=usage.requests,
        cachedTokens=cached,
        reasoningTokens=reasoning,
        modelName=resolved_name,
        costUsd=cost_usd,
    )


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
                balance=account_data.balance,
                holdings=account_data.holdings,
                recent_activity=recent_activity,
            )

            # === RESEARCH PHASE ===
            research_result = await self._run_market_analyst(
                ctx=ctx,
                mcp_pool=mcp_pool,
            )
            ctx.research = research_result

            # === DECISION PHASE ===
            decision_result = await self._run_decision_maker(
                ctx=ctx,
                mcp_pool=mcp_pool,
                force_trade=force_trade,
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
                )
            else:
                # HOLD decision - skip execution phase
                ctx.execution_result = ExecutionResult(
                    execution_status=PhaseStatus.SKIPPED,
                    trade_id=None,
                    execution_error=None,
                )

            # === FINALIZATION ===
            await self._finalize_run(ctx)

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
            await self._handle_cycle_error(e, ctx)
            raise

    def _extract_run_telemetry(
        self,
        result: RunResult,
        model_name: str,
        agent_label: str,
    ) -> tuple[list[ToolCallDto], UsageMetrics]:
        """Extract tool calls + usage metrics from an SDK RunResult and log both.

        Used by `_run_market_analyst` and `_run_decision_maker` to keep both
        agent runners structurally symmetric.
        """
        parsed_calls = extract_tool_calls(result.new_items)
        tool_calls = [
            ToolCallDto(
                tool=pc.name,
                params=pc.params,
                error=pc.is_error if pc.is_error else None,
                errorMessage=pc.error_message,
            )
            for pc in parsed_calls
        ]
        logger.info(f"🔧 {agent_label} made {len(tool_calls)} tool calls")

        usage = result.context_wrapper.usage
        usage_metrics = _extract_usage_metrics(usage, model_name=model_name)
        logger.info(
            f"📊 {agent_label} usage: {usage_metrics.tokensUsed} tokens, "
            f"model={usage_metrics.modelName}"
        )
        return tool_calls, usage_metrics

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

        # Log portfolio access (inline observability — preserves the
        # "Portfolio data fetched" semantic that the previously-removed
        # parallel tracking system used to record.)
        portfolio_data = {
            "balance": round(ctx.balance, 2),
            "holdings_count": len(ctx.holdings),
            "symbols": [h.symbol for h in ctx.holdings] if ctx.holdings else []
        }
        logger.debug(
            "Portfolio data fetched: balance=$%.2f, positions=%d, symbols=%s",
            ctx.balance,
            len(ctx.holdings),
            portfolio_data["symbols"],
        )

        # Create Market Analyst using async factory pattern
        market_analyst = await MarketAnalyst.create(
            agent_name=ctx.agent_name,
            agent_id=ctx.agent_id,
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
            max_positions=MAX_POSITIONS,
        )

        # Build prompt using OO interface
        research_prompt = market_analyst.build_prompt(research_context)

        # Capture prompts for observability (before agent execution).
        # Agent.instructions is typed `str | Callable[..., str] | None` by the
        # SDK; the project's RunContext field is `str | None`. Sibling agents
        # currently always set instructions to a str (see MarketAnalyst.create
        # / DecisionMaker.create) so the str branch is always taken at runtime.
        # The isinstance narrow + debug log keep prompt capture safe AND
        # observable if anyone swaps to dynamic-callable instructions later.
        instructions = market_analyst.agent.instructions
        if not isinstance(instructions, str) and instructions is not None:
            logger.debug(
                "market_analyst.agent.instructions is callable, not str — "
                "skipping prompt capture for observability"
            )
        ctx.market_analyst_system_prompt = instructions if isinstance(instructions, str) else None
        ctx.market_analyst_task_prompt = research_prompt

        logger.info(f"🔬 Running Market Analyst for {ctx.agent_name}...")

        # Run Market Analyst with guardrail retry loop.
        # If the output guardrail rejects the response, the retry function
        # reconstructs the conversation and retries so the LLM can self-correct.
        result = await run_with_guardrail_retry(
            market_analyst.agent,
            research_prompt,
            max_attempts=RESEARCH_MAX_ATTEMPTS,
            max_turns=AGENT_MAX_TURNS,
            agent_name=ctx.agent_name,
        )

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
            for source in research_response.webSources
        ]
        # Add system context source for portfolio
        sources.append(SourceDto.system_context(f"Portfolio context: {json.dumps(portfolio_data)}"))
        sources.append(SourceDto.system_context("Retrieved 30-day trading activity history"))

        # Calculate research latency
        research_latency_ms = int(
            (datetime.now() - research_start_time).total_seconds() * 1000
        )
        logger.info(f"📊 Market Analyst completed in {research_latency_ms}ms")

        # Extract tool calls + usage metrics (DRY helper — see _extract_run_telemetry)
        tool_calls, usage_metrics = self._extract_run_telemetry(
            result, model_name=market_analyst.model_name, agent_label="Market Analyst"
        )

        # Prices are now carried directly in CandidateStock objects within
        # research_response.candidates — no brittle tool-output parsing needed.
        # Extract symbol strings for DB storage (backend expects list[str]).
        candidate_symbols = [c.symbol for c in research_response.candidates]

        logger.info(
            f"✅ Market Analyst found {len(candidate_symbols)} candidates "
            f"with prices, {len(sources)} sources"
        )

        return ResearchResult(
            research_response=research_response,
            candidates=candidate_symbols,
            sources=sources,
            notes=research_response.summary,
            tool_calls=tool_calls,
            usage_metrics=usage_metrics,
            research_latency_ms=research_latency_ms,
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
            agent_style=ctx.agent_style,
        )

        # Type narrowing: research is guaranteed set by _run_market_analyst
        assert ctx.research is not None, "research must be set before decision phase"

        # Build typed context (class converts to strings internally)
        decision_context = DecisionContext(
            agent_name=ctx.agent_name,
            agent_style=ctx.agent_style,
            research_response=ctx.research.research_response,
            balance=ctx.balance,
            holdings=ctx.holdings,
            recent_activity=ctx.recent_activity,
            force_trade=force_trade,
            max_positions=MAX_POSITIONS,
        )

        # Build prompt using OO interface
        decision_prompt = decision_maker.build_prompt(decision_context)

        # Capture prompts for observability (before agent execution).
        # See _run_market_analyst for the rationale behind the isinstance narrow.
        instructions = decision_maker.agent.instructions
        if not isinstance(instructions, str) and instructions is not None:
            logger.debug(
                "decision_maker.agent.instructions is callable, not str — "
                "skipping prompt capture for observability"
            )
        ctx.decision_maker_system_prompt = instructions if isinstance(instructions, str) else None
        ctx.decision_maker_task_prompt = decision_prompt

        logger.info(f"🧠 Running Decision Maker for {ctx.agent_name}...")

        # Run Decision Maker agent - get structured output directly
        result = await Runner.run(decision_maker.agent, decision_prompt, max_turns=AGENT_MAX_TURNS)

        # Extract TradingDecision - type-safe using SDK's final_output_as()
        try:
            decision = result.final_output_as(TradingDecision)
        except TypeError as e:
            raise RuntimeError(
                f"Decision Maker for {ctx.agent_name} failed to produce TradingDecision: {e}"
            ) from e

        logger.info(f"✅ Decision Maker: {decision.action} {decision.symbol or ''}")

        # Extract tool calls + usage metrics (DRY helper — see _extract_run_telemetry)
        tool_calls, usage_metrics = self._extract_run_telemetry(
            result, model_name=decision_maker.model_name, agent_label="Decision Maker"
        )

        # Calculate decision latency
        decision_latency_ms = int(
            (datetime.now() - decision_start_time).total_seconds() * 1000
        )
        logger.info(f"📊 Decision Maker completed in {decision_latency_ms}ms")

        return DecisionResult(
            decision=decision,
            decision_start_time=decision_start_time,
            tool_calls=tool_calls,
            usage_metrics=usage_metrics,
        )

    async def _execute_trade(
        self,
        run_id: int,
        agent_id: int,
        decision: TradingDecision,
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

        # Update to TRADING phase
        await update_phase(run_id, RunPhase.TRADING)

        # Broadcast: TRADING
        broadcast_status(agent_id, self.name, PHASE_TRADING, "Executing trade", 90)

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

    async def _finalize_run(self, ctx: RunContext) -> None:
        """Complete run with all data.

        Args:
            ctx: RunContext with all data to persist

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

        # Complete the run via API
        await complete_run(ctx.run_id, complete_data)

        # Broadcast: COMPLETED — outcome_message branches on execution_status
        # so a FAILED BUY/SELL isn't mislabeled as 'No trades (HOLD decision)'
        # (the prior implementation branched on trade_id truthiness, which
        # collapsed FAILED and SKIPPED into the same message).
        status = ctx.execution_result.execution_status
        if status == PhaseStatus.COMPLETED:
            outcome_message = "Completed - 1 trade executed"
        elif status == PhaseStatus.SKIPPED:
            outcome_message = "Completed - No trades (HOLD decision)"
        elif status == PhaseStatus.FAILED:
            outcome_message = "Completed - Trade attempted but failed"
        else:
            outcome_message = f"Completed - Unknown status: {status}"
        broadcast_status(
            ctx.agent_id,
            ctx.agent_name,
            PHASE_COMPLETED,
            outcome_message,
            100,
            outcome=outcome_message,
        )

    async def _handle_cycle_error(self, error: Exception, ctx: RunContext | None) -> None:
        """Handle cycle execution error.

        Best-effort error recording — never masks the original exception.

        Args:
            error: Exception that occurred
            ctx: RunContext if available (may be None if Phase 1 failed)
        """
        agent_id = ctx.agent_id if ctx else self.agent_id
        agent_name = ctx.agent_name if ctx else self.name
        run_id = ctx.run_id if ctx else None

        logger.error(f"Cycle error for {agent_name}: {error}")

        # Broadcast: ERROR
        broadcast_status(
            agent_id,
            agent_name,
            PHASE_ERROR,
            f"Error: {str(error)}",
            0,
            outcome=f"Failed: {str(error)}",
        )

        # Update run to FAILED state. Do NOT call complete_run() — that
        # would override FAILED back to COMPLETED. Just set the failed phase.
        if run_id is not None:
            try:
                error_msg = str(error)[:MAX_ERROR_MESSAGE_LEN] or "Unknown error"
                await update_phase(run_id, RunPhase.FAILED, error_message=error_msg)
            except Exception as cleanup_err:
                logger.error(
                    f"Failed to record error state for run {run_id}: {cleanup_err}"
                )

