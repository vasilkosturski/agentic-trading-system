"""Research phase — runs the Market Analyst agent end-to-end.

Extracted from ``AgentExecutor._run_market_analyst`` (Task 6 of the
agent-executor decomposition plan at
``docs/superpowers/plans/2026-05-13-aegr-decomposition.md``). The
function reads only ``ctx``; there is no ``self`` to thread.

The prompt-capture side effect into
``ctx.market_analyst_system_prompt`` / ``ctx.market_analyst_task_prompt``
is preserved exactly as it was in the original method (isinstance-narrow
pattern that keeps the observable DEBUG log when ``agent.instructions``
is a dynamic callable rather than a static str).
"""

import json
import logging
from datetime import datetime

from guardrail_retry import run_with_guardrail_retry
from market_analyst import MarketAnalyst, MarketAnalystContext
from models import ResearchResponse
from models.orchestration import ResearchResult, RunContext
from models.run_tracking import SourceDto
from telemetry import extract_run_telemetry

# Constants live in agent_executor.py for now; Task 10 of the
# decomposition plan may reconcile if a shared constants module emerges.
# Importing here is safe because agent_executor imports run_research_phase
# AFTER its module-level constants are declared, so by the time this
# module is initialized those names are already bound on agent_executor.
from agent_executor import AGENT_MAX_TURNS, MAX_POSITIONS, RESEARCH_MAX_ATTEMPTS

logger = logging.getLogger(__name__)


async def run_research_phase(
    ctx: RunContext,
    mcp_pool,  # MCPPool
) -> ResearchResult:
    """Run Market Analyst agent for research.

    Args:
        ctx: RunContext with agent info and account data
        mcp_pool: MCP pool for creating agent

    Returns:
        ResearchResult with research findings

    Side effect:
        Writes captured prompts into ``ctx.market_analyst_system_prompt``
        / ``ctx.market_analyst_task_prompt``.
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

    # Extract tool calls + usage metrics (DRY helper — see telemetry.extract_run_telemetry)
    tool_calls, usage_metrics = extract_run_telemetry(
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
