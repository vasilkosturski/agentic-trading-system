"""Finalization phase — assembles run data and completes the run.

Extracted from ``AgentExecutor._finalize_run`` (Task 9 of the
agent-executor decomposition plan at
``docs/superpowers/plans/2026-05-13-aegr-decomposition.md``). Mirror of
``phases/research_phase.py`` (Task 6), ``phases/decision_phase.py``
(Task 7), and ``phases/execution_phase.py`` (Task 8). Pure body lift —
the original method had no ``self.`` references, so this is a clean
mechanical extraction.

The ``outcome_message`` if/elif/elif/else block (Minor #12 fix) is
preserved verbatim: it branches on ``ctx.execution_result.execution_status``
against COMPLETED / SKIPPED / FAILED / fallback. The pre-fix bug branched
on ``ctx.trade_id`` truthiness, mislabeling a FAILED BUY (trade_id=None)
as "Completed - No trades (HOLD decision)". Do not rewrite this block.
"""

import logging
from datetime import datetime

from models.orchestration import RunContext
from models.run_tracking import (
    CompleteRunData,
    DecisionPhaseData,
    ExecutionPhaseData,
    PhaseStatus,
    ReasoningDto,
    ResearchPhaseData,
    TradeDecision,
)
from run_lifecycle import RunLifecycle

# Constants live in agent_executor.py for now; Task 10 of the
# decomposition plan may reconcile if a shared constants module emerges.
# Importing here is safe because agent_executor imports run_finalization_phase
# AFTER its module-level constants are declared, so by the time this
# module is initialized those names are already bound on agent_executor.
from agent_executor import MAX_REASONING_FIELD_LEN

logger = logging.getLogger(__name__)


async def run_finalization_phase(ctx: RunContext, lifecycle: RunLifecycle) -> None:
    """Complete run with all data.

    Args:
        ctx: RunContext with all data to persist
        lifecycle: RunLifecycle instance driving phase transitions

    Preconditions (enforced via assertions):
        - research: set by run_research_phase
        - decision_result: set by run_decision_phase
        - execution_result: set by execute_cycle (BUY/SELL branch or HOLD short-circuit)
    """
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

    # Branch on execution_status, not trade_id — FAILED and SKIPPED both
    # have trade_id=None but need distinct outcome messages.
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
