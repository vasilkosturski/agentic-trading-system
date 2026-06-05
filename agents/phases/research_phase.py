import json
import logging
from datetime import datetime

from agent_executor import AGENT_MAX_TURNS, MAX_POSITIONS, RESEARCH_MAX_ATTEMPTS
from ai_agents.guardrail_retry import run_with_guardrail_retry
from ai_agents.market_analyst import MarketAnalyst, MarketAnalystContext
from infra.telemetry import extract_run_telemetry
from models import ResearchResponse
from models.orchestration import ResearchResult, RunContext
from models.run_tracking import SourceDto

logger = logging.getLogger(__name__)


async def run_research_phase(
    ctx: RunContext,
    mcp_pool,
) -> ResearchResult:
    """Side effect: writes captured prompts into ctx.market_analyst_system_prompt / ctx.market_analyst_task_prompt."""
    research_start_time = datetime.now()

    portfolio_data = {
        "balance": round(ctx.balance, 2),
        "holdings_count": len(ctx.holdings),
        "symbols": [h.symbol for h in ctx.holdings] if ctx.holdings else [],
    }
    logger.debug(
        "Portfolio data fetched: balance=$%.2f, positions=%d, symbols=%s",
        ctx.balance,
        len(ctx.holdings),
        portfolio_data["symbols"],
    )

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

    # Agent.instructions is typed `str | Callable[..., str] | None` by the
    # SDK but project agents always set a str; the isinstance narrow keeps
    # prompt capture safe if anyone later swaps to a dynamic callable.
    instructions = market_analyst.agent.instructions
    if not isinstance(instructions, str) and instructions is not None:
        logger.debug(
            "ai_agents.market_analyst.agent.instructions is callable, not str — "
            "skipping prompt capture for observability"
        )
    ctx.market_analyst_system_prompt = instructions if isinstance(instructions, str) else None
    ctx.market_analyst_task_prompt = research_prompt

    logger.info(f"🔬 Running Market Analyst for {ctx.agent_name}...")

    result = await run_with_guardrail_retry(
        market_analyst.agent,
        research_prompt,
        max_attempts=RESEARCH_MAX_ATTEMPTS,
        max_turns=AGENT_MAX_TURNS,
        agent_name=ctx.agent_name,
    )

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
    )
