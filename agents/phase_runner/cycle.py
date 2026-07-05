"""One trading cycle, top to bottom.

``run_cycle`` is the public Interface. It owns the full sequence:
init → research → decision → execution (BUY/SELL only) → finalization, with
``Lifecycle`` driving the persisted phase transitions and broadcasts. Errors
are caught and routed through ``Lifecycle.fail`` — the cycle never raises.

Each ``_run_*`` helper is private; together with the cycle body they read as
one narrative. Shared SDK telemetry / prompt-capture logic lives in
``_telemetry.py``; backend writes go through ``Lifecycle``.
"""

import json
import logging
from datetime import datetime

from agents import Runner
from agents.exceptions import OutputGuardrailTripwireTriggered

from ai_agents.decision_maker import DecisionContext, DecisionMaker
from ai_agents.guardrail_retry import run_with_guardrail_retry
from ai_agents.market_analyst import MarketAnalyst, MarketAnalystContext
from backend.client import get_backend_client
from config import config
from infra.constants import MAX_REASONING_FIELD_LEN
from models import ResearchResponse, TradingDecision
from models.api_responses import RecentActivityResponse
from models.investment_style import InvestmentStyle
from models.orchestration import (
    AccountData,
    DecisionResult,
    ExecutionResult,
    ResearchResult,
    RunContext,
)
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
from phase_runner._lifecycle import Lifecycle
from phase_runner._telemetry import capture_agent_prompts, extract_run_telemetry

logger = logging.getLogger(__name__)

RESEARCH_MAX_ATTEMPTS = 3
AGENT_MAX_TURNS = 30
MAX_POSITIONS = 10
RECENT_ACTIVITY_LOOKBACK_DAYS = 30


async def run_cycle(
    *,
    agent_id: int,
    name: str,
    agent_style: InvestmentStyle,
    mcp_pool,  # MCPPool
    model_name: str | None = None,
    force_trade: bool = False,
) -> None:
    """Execute one complete portfolio-review cycle.

    Sequential phases (research → decision → execution → finalization) bound
    to a single ``Lifecycle`` instance so concurrent cycles never share state.
    The trading-system orchestrator creates one ``asyncio`` task per agent and
    fans out via ``asyncio.gather``; each task is an independent ``run_cycle``
    call.

    Args:
        agent_id: Unique agent identifier (backend-assigned).
        name: Agent name (e.g. "Warren").
        agent_style: Investment-style enum.
        mcp_pool: MCP pool for creating agents.
        model_name: OpenAI model name; defaults to ``config.OPENAI_MODEL``.
        force_trade: If True, the decision agent must produce BUY/SELL (no HOLD).

    Returns ``None``: the cycle is pure side-effect (DB writes + broadcasts).
    Errors are recorded via ``Lifecycle.fail`` and swallowed — every caller
    today logs at the boundary and continues; embedding that contract here
    keeps it from leaking across each caller.
    """
    resolved_model = model_name if model_name is not None else config.OPENAI_MODEL

    logger.info(
        f"🤖 {name} starting portfolio review at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    lifecycle = Lifecycle(agent_id, name)
    ctx: RunContext | None = None

    try:
        research_start_time = datetime.now()
        run_id = await lifecycle.start()

        account_data = await _fetch_account_data(agent_id)
        recent_activity = await _fetch_recent_activity(agent_id)

        ctx = RunContext(
            run_id=run_id,
            agent_id=agent_id,
            agent_name=name,
            agent_style=agent_style,
            model_name=resolved_model,
            research_start_time=research_start_time,
            balance=account_data.balance,
            holdings=account_data.holdings,
            recent_activity=recent_activity,
        )

        ctx.research = await _run_research(ctx, mcp_pool, lifecycle)

        await lifecycle.transition_to_deciding(run_id)
        ctx.decision_result = await _run_decision(ctx, mcp_pool, force_trade, lifecycle)

        ctx.decision_sources = _build_decision_sources(ctx)

        if ctx.decision_result.decision.action in (TradeDecision.BUY, TradeDecision.SELL):
            await lifecycle.transition_to_trading(run_id)
            ctx.execution_result = await _run_execution(ctx, name)
        else:
            ctx.execution_result = ExecutionResult(
                execution_status=PhaseStatus.SKIPPED,
                trade_id=None,
                execution_error=None,
            )

        await _run_finalization(ctx, lifecycle)

        logger.info(
            f"✅ {name} completed portfolio review at "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    except Exception as error:
        # ``Lifecycle.fail`` swallows its own cleanup errors. Guard here too so
        # a contract regression there can't propagate either: the only place
        # cycle errors should surface is the logs and the FAILED run row.
        run_id_for_fail = ctx.run_id if ctx else None
        try:
            await lifecycle.fail(run_id_for_fail, error)
        except Exception:
            logger.exception(
                "Cleanup via Lifecycle.fail raised while handling cycle "
                "error; cycle ends here regardless"
            )


# ---------------------------------------------------------------------------
# Account / activity fetch helpers
# ---------------------------------------------------------------------------


async def _fetch_account_data(agent_id: int) -> AccountData:
    """One HTTP call for balance + holdings (account-report endpoint)."""
    client = get_backend_client()
    report = await client.get_account_report(agent_id)
    return AccountData(balance=report.balance, holdings=report.holdings)


async def _fetch_recent_activity(agent_id: int) -> RecentActivityResponse:
    """Last ``RECENT_ACTIVITY_LOOKBACK_DAYS`` of runs + trades, for context."""
    client = get_backend_client()
    result = await client.get_recent_activity(agent_id, days=RECENT_ACTIVITY_LOOKBACK_DAYS)
    logger.info(
        f"📊 Context prepared: {result.computed_total_runs} runs, "
        f"{result.computed_total_trades} trades (30 days)"
    )
    return result


def _build_decision_sources(ctx: RunContext) -> list[SourceDto]:
    """Trace the data inputs that informed the decision (audit trail)."""
    assert ctx.research is not None  # set by _run_research
    return [
        *[
            SourceDto.web(title=s.title, url=s.url)
            for s in ctx.research.research_response.webSources
        ],
        SourceDto.system_context(f"Portfolio: ${ctx.balance:,.2f}, {len(ctx.holdings)} positions"),
        SourceDto.system_context(
            f"Recent activity: {len(ctx.recent_activity.runs) if ctx.recent_activity else 0} runs"
        ),
    ]


# ---------------------------------------------------------------------------
# Phase helpers
# ---------------------------------------------------------------------------


async def _run_research(ctx: RunContext, mcp_pool, lifecycle: Lifecycle) -> ResearchResult:
    """Run Market Analyst end-to-end. Side-effect: writes prompts back onto ``ctx``."""
    research_start_time = datetime.now()

    portfolio_data = {
        "balance": round(ctx.balance, 2),
        "holdings_count": len(ctx.holdings),
        "symbols": [h.symbol for h in ctx.holdings] if ctx.holdings else [],
    }

    market_analyst = await MarketAnalyst.create(
        agent_name=ctx.agent_name,
        mcp_pool=mcp_pool,
        model_name=ctx.model_name,
    )

    research_context = MarketAnalystContext(
        agent_name=ctx.agent_name,
        agent_style=ctx.agent_style,
        balance=ctx.balance,
        holdings=ctx.holdings,
        recent_activity=ctx.recent_activity,
        max_positions=MAX_POSITIONS,
    )

    research_prompt = market_analyst.build_prompt(research_context)
    (
        ctx.market_analyst_system_prompt,
        ctx.market_analyst_task_prompt,
    ) = capture_agent_prompts(market_analyst.agent, research_prompt)

    logger.info(f"🔬 Running Market Analyst for {ctx.agent_name}...")

    try:
        guardrail_outcome = await run_with_guardrail_retry(
            market_analyst.agent,
            research_prompt,
            max_attempts=RESEARCH_MAX_ATTEMPTS,
            max_turns=AGENT_MAX_TURNS,
            agent_name=ctx.agent_name,
            run_id=ctx.run_id,
        )
    except OutputGuardrailTripwireTriggered as e:
        # Guardrail loop exhausted. The helper attaches a ``GuardrailOutcome`` to
        # the re-raised exception; persist it via the best-effort lifecycle method
        # so the audit DB has an ``outcome='exhausted'`` row even though
        # ``complete_run`` is skipped on the FAILED path.
        exhausted_outcome = getattr(e, "guardrail_outcome", None)
        if exhausted_outcome is not None:
            await lifecycle.record_phase_failure(ctx.run_id, "RESEARCH", exhausted_outcome)
        raise
    result = guardrail_outcome.result
    assert result is not None, "guardrail_outcome.result is None only when the helper re-raises"

    try:
        research_response = result.final_output_as(ResearchResponse)
    except TypeError as e:
        raise RuntimeError(
            f"Market Analyst for {ctx.agent_name} failed to produce ResearchResponse: {e}"
        ) from e

    sources = [
        SourceDto.web(title=source.title, url=source.url) for source in research_response.webSources
    ]
    sources.append(SourceDto.system_context(f"Portfolio context: {json.dumps(portfolio_data)}"))
    sources.append(SourceDto.system_context("Retrieved 30-day trading activity history"))

    research_latency_ms = int((datetime.now() - research_start_time).total_seconds() * 1000)
    logger.info(f"📊 Market Analyst completed in {research_latency_ms}ms")

    tool_calls, usage_metrics = extract_run_telemetry(
        result, model_name=market_analyst.model_name, agent_label="Market Analyst"
    )

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
        guardrail_attempts=guardrail_outcome.attempts_used,
        guardrail_issues=guardrail_outcome.last_issues or None,
        guardrail_outcome=guardrail_outcome.outcome,
        guardrail_failed_output=guardrail_outcome.failed_output,
    )


async def _run_decision(
    ctx: RunContext,
    mcp_pool,
    force_trade: bool,
    lifecycle: Lifecycle,
) -> DecisionResult:
    """Run Decision Maker end-to-end. Side-effect: writes prompts back onto ``ctx``."""
    decision_start_time = datetime.now()

    decision_maker = await DecisionMaker.create(
        agent_name=ctx.agent_name,
        agent_id=ctx.agent_id,
        mcp_pool=mcp_pool,
        model_name=ctx.model_name,
        agent_style=ctx.agent_style,
    )

    assert ctx.research is not None, "research must be set before decision phase"

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

    decision_prompt = decision_maker.build_prompt(decision_context)
    (
        ctx.decision_maker_system_prompt,
        ctx.decision_maker_task_prompt,
    ) = capture_agent_prompts(decision_maker.agent, decision_prompt)

    logger.info(f"🧠 Running Decision Maker for {ctx.agent_name}...")

    # The bare Runner.run path here only raises OutputGuardrailTripwireTriggered
    # with .guardrail_outcome attached once a retry helper wraps it. Today only
    # the analyst path uses such a wrapper, but the catch is preserved so
    # decision-side guardrails get the same exhaustion-stub persistence.
    try:
        result = await Runner.run(decision_maker.agent, decision_prompt, max_turns=AGENT_MAX_TURNS)
    except OutputGuardrailTripwireTriggered as e:
        exhausted_outcome = getattr(e, "guardrail_outcome", None)
        if exhausted_outcome is not None:
            await lifecycle.record_phase_failure(ctx.run_id, "DECISION", exhausted_outcome)
        raise

    try:
        decision = result.final_output_as(TradingDecision)
    except TypeError as e:
        raise RuntimeError(
            f"Decision Maker for {ctx.agent_name} failed to produce TradingDecision: {e}"
        ) from e

    logger.info(f"✅ Decision Maker: {decision.action} {decision.symbol or ''}")

    tool_calls, usage_metrics = extract_run_telemetry(
        result, model_name=decision_maker.model_name, agent_label="Decision Maker"
    )

    decision_latency_ms = int((datetime.now() - decision_start_time).total_seconds() * 1000)
    logger.info(f"📊 Decision Maker completed in {decision_latency_ms}ms")

    return DecisionResult(
        decision=decision,
        decision_start_time=decision_start_time,
        tool_calls=tool_calls,
        usage_metrics=usage_metrics,
    )


async def _run_execution(ctx: RunContext, agent_name: str) -> ExecutionResult:
    """Dispatch a BUY or SELL trade via BackendClient. HOLD is filtered upstream."""
    assert ctx.decision_result is not None
    decision = ctx.decision_result.decision
    action = decision.action
    symbol = decision.symbol
    quantity = decision.quantity

    logger.info(f"✅ Validated decision: {action} {symbol or ''}")
    logger.info(f"🟡 ABOUT TO EXECUTE: decision={decision}")
    logger.info(f"🟢 EXECUTING: {action} {quantity} shares of {symbol}")

    client = get_backend_client()
    trade_id: int | None = None
    execution_status: PhaseStatus
    execution_error: str | None = None

    try:
        if action == TradeDecision.BUY:
            result = await client.buy_shares(ctx.agent_id, symbol, quantity, run_id=ctx.run_id)
        else:  # SELL
            result = await client.sell_shares(ctx.agent_id, symbol, quantity, run_id=ctx.run_id)
        logger.info(f"{agent_name} {action.value.lower()} {quantity} shares of {symbol}")
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


async def _run_finalization(ctx: RunContext, lifecycle: Lifecycle) -> None:
    """Assemble ``CompleteRunData`` from accumulated ``ctx`` and complete the run."""
    assert ctx.research is not None, "research must be set"
    assert ctx.decision_result is not None, "decision_result must be set"
    assert ctx.execution_result is not None, "execution_result must be set"

    # research_latency_ms is owned by the research phase (wall-clocked there);
    # don't recompute it here, otherwise it drifts by the decision-setup time.
    decision_latency_ms = int(
        (datetime.now() - ctx.decision_result.decision_start_time).total_seconds() * 1000
    )
    research_latency_ms = ctx.research.research_latency_ms

    decision = ctx.decision_result.decision
    trade_decision = TradeDecision(decision.action.value)
    symbol = decision.symbol if decision.action in (TradeDecision.BUY, TradeDecision.SELL) else None
    quantity = (
        decision.quantity if decision.action in (TradeDecision.BUY, TradeDecision.SELL) else None
    )

    reasoning = ReasoningDto(
        rationale=decision.rationale[:MAX_REASONING_FIELD_LEN] if decision.rationale else None,
        portfolioContext=decision.portfolioContext[:MAX_REASONING_FIELD_LEN]
        if decision.portfolioContext
        else None,
        historicalContext=decision.historicalContext[:MAX_REASONING_FIELD_LEN]
        if decision.historicalContext
        else None,
        researchContext=decision.researchContext[:MAX_REASONING_FIELD_LEN]
        if decision.researchContext
        else None,
    )

    research_data = ResearchPhaseData(
        candidates=ctx.research.candidates,
        sources=ctx.research.sources,
        notes=ctx.research.notes,
        toolCalls=ctx.research.tool_calls,
        latencyMs=research_latency_ms,
        metrics=ctx.research.usage_metrics,
        systemPrompt=ctx.market_analyst_system_prompt,
        taskPrompt=ctx.market_analyst_task_prompt,
        guardrailAttempts=ctx.research.guardrail_attempts,
        guardrailIssues=ctx.research.guardrail_issues,
        guardrailOutcome=ctx.research.guardrail_outcome,
        guardrailFailedOutput=ctx.research.guardrail_failed_output,
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
        guardrailAttempts=ctx.decision_result.guardrail_attempts,
        guardrailIssues=ctx.decision_result.guardrail_issues,
        guardrailOutcome=ctx.decision_result.guardrail_outcome,
        guardrailFailedOutput=ctx.decision_result.guardrail_failed_output,
    )

    execution_data = ExecutionPhaseData(
        tradeId=ctx.execution_result.trade_id,
        status=ctx.execution_result.execution_status,
        errorDetails=ctx.execution_result.execution_error,
    )

    complete_data = CompleteRunData(
        research=research_data,
        decision=decision_data,
        execution=execution_data,
    )

    # Branch on execution_status, not trade_id — FAILED and SKIPPED both have
    # trade_id=None but need distinct outcome messages.
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
