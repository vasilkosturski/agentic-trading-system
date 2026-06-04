"""Decision phase — runs the Decision Maker agent end-to-end.

Extracted from ``AgentExecutor._run_decision_maker`` (Task 7 of the
agent-executor decomposition plan at
``docs/superpowers/plans/2026-05-13-aegr-decomposition.md``). Mirror of
``phases/research_phase.py`` (Task 6), but for the Decision Maker.

The prompt-capture side effect into
``ctx.decision_maker_system_prompt`` / ``ctx.decision_maker_task_prompt``
is preserved exactly as it was in the original method (isinstance-narrow
pattern that keeps the observable DEBUG log when ``agent.instructions``
is a dynamic callable rather than a static str).
"""

import logging
from datetime import datetime

from agents import Runner

# Constants live in agent_executor.py for now; Task 10 of the
# decomposition plan may reconcile if a shared constants module emerges.
# Importing here is safe because agent_executor imports run_decision_phase
# AFTER its module-level constants are declared, so by the time this
# module is initialized those names are already bound on agent_executor.
from agent_executor import AGENT_MAX_TURNS, MAX_POSITIONS
from ai_agents.decision_maker import DecisionContext, DecisionMaker
from backend.run_lifecycle import RunLifecycle
from infra.telemetry import extract_run_telemetry
from models import TradingDecision
from models.orchestration import DecisionResult, RunContext

logger = logging.getLogger(__name__)


async def run_decision_phase(
    ctx: RunContext,
    mcp_pool,  # MCPPool
    force_trade: bool,
    lifecycle: RunLifecycle,
) -> DecisionResult:
    """Run Decision Maker agent for trading decision.

    Args:
        ctx: RunContext with research results and account data
        mcp_pool: MCP pool for creating agent
        force_trade: If True, agent must make BUY/SELL (no HOLD)
        lifecycle: RunLifecycle instance driving phase transitions

    Returns:
        DecisionResult with decision and timing

    Side effect:
        Writes captured prompts into ``ctx.decision_maker_system_prompt``
        / ``ctx.decision_maker_task_prompt``. Also calls
        ``lifecycle.transition_to_deciding(ctx.run_id)`` at the top to
        advance the run's persisted phase.
    """
    await lifecycle.transition_to_deciding(ctx.run_id)
    decision_start_time = datetime.now()

    # Create Decision Maker using async factory pattern
    decision_maker = await DecisionMaker.create(
        agent_name=ctx.agent_name,
        agent_id=ctx.agent_id,
        mcp_pool=mcp_pool,
        model_name=ctx.model_name,
        agent_style=ctx.agent_style,
    )

    # Type narrowing: research is guaranteed set by run_research_phase
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
    # See phases/research_phase.py for the rationale behind the isinstance narrow.
    instructions = decision_maker.agent.instructions
    if not isinstance(instructions, str) and instructions is not None:
        logger.debug(
            "ai_agents.decision_maker.agent.instructions is callable, not str — "
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

    # Extract tool calls + usage metrics (DRY helper — see telemetry.extract_run_telemetry)
    tool_calls, usage_metrics = extract_run_telemetry(
        result, model_name=decision_maker.model_name, agent_label="Decision Maker"
    )

    # Calculate decision latency
    decision_latency_ms = int((datetime.now() - decision_start_time).total_seconds() * 1000)
    logger.info(f"📊 Decision Maker completed in {decision_latency_ms}ms")

    return DecisionResult(
        decision=decision,
        decision_start_time=decision_start_time,
        tool_calls=tool_calls,
        usage_metrics=usage_metrics,
    )
