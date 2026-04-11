"""E2E smoke test for Market Analyst with real integrations.

Run with: pytest tests/e2e/test_market_analyst_e2e.py -v -s

WARNING: This test costs real $ (Brave Search + OpenAI). Run sparingly.
"""

import json
import logging
from contextlib import AsyncExitStack
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import pytest
from agents.mcp import MCPServerStdio
from agents.exceptions import MaxTurnsExceeded

from market_analyst import MarketAnalyst, MarketAnalystContext
from mcp_types import MCPPool
from mcp_params import get_mcp_server_params
from models.llm_output import ResearchResponse

logger = logging.getLogger("e2e_tests.market_analyst")

_RESULTS_DIR = Path(__file__).parent / "results"


def _dump_result_to_json(
    test_name: str,
    result,
    system_prompt: str = "",
    task_prompt: str = "",
) -> None:
    """Serialize AgentRunResult to JSON for manual inspection.

    Writes to tests/e2e/results/{test_name}_{timestamp}.json.
    Silently logs on failure -- must never mask the real test outcome.
    """
    try:
        _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"{test_name}_{ts}.json"

        # Build serializable dict
        output_data = None
        if result.output is not None:
            # Pydantic model -- use .model_dump()
            output_data = result.output.model_dump()

        data = {
            "test_name": test_name,
            "timestamp": ts,
            "system_prompt": system_prompt,
            "task_prompt": task_prompt,
            "output": output_data,
            "tool_calls": [asdict(tc) for tc in result.tool_calls],
            "tool_errors": [asdict(tc) for tc in result.tool_errors],
        }

        filepath = _RESULTS_DIR / filename
        filepath.write_text(json.dumps(data, indent=2, default=str))
        logger.info(f"Result dumped to {filepath}")
    except Exception:
        logger.exception("Failed to dump result to JSON")


@pytest.fixture
async def real_mcp_pool():
    """Create a real MCP pool with Brave Search and Fetch."""
    async with AsyncExitStack() as stack:
        mcp_params = get_mcp_server_params()
        mcp_pool: MCPPool = {}

        for mcp_name, params in mcp_params.items():
            server = await stack.enter_async_context(
                MCPServerStdio(params, client_session_timeout_seconds=120)
            )
            mcp_pool[mcp_name] = server

        logger.info(f"MCP pool created: {list(mcp_pool.keys())}")
        yield mcp_pool


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.costly
@pytest.mark.usefixtures("require_openai_api_key", "require_brave_api_key", "require_backend", "seed_test_data")
class TestMarketAnalystE2E:
    """E2E smoke test for Market Analyst."""

    @pytest.mark.asyncio
    async def test_market_analyst_returns_candidates(
        self,
        real_mcp_pool: MCPPool,
        test_agent_id,
        test_agent_name,
        test_agent_style,
        test_model_name,
        real_agent_holdings,
        real_agent_balance,
        real_recent_activity,
    ):
        """Smoke test: Market Analyst finds stock candidates.

        Verifies:
        1. Real Brave Search API call works
        2. Real OpenAI API call works
        3. Returns valid ResearchResponse with candidates
        4. Uses real backend data (seeded agent, holdings, activity)

        Note: require_* fixtures validate prerequisites early,
        avoiding expensive LLM calls if credentials or backend are missing.
        """
        logger.info("=" * 60)
        logger.info("E2E SMOKE TEST: Market Analyst")
        logger.info("=" * 60)
        logger.info(f"Agent: {test_agent_name} ({test_agent_style})")
        logger.info(f"Balance: {real_agent_balance}")
        logger.info(f"Holdings: {len(real_agent_holdings)} positions")

        # Create Market Analyst using async factory
        market_analyst = await MarketAnalyst.create(
            agent_name=test_agent_name,
            agent_id=test_agent_id,
            mcp_pool=real_mcp_pool,
            model_name=test_model_name,
        )

        # Build context using real backend data
        context = MarketAnalystContext(
            agent_name=test_agent_name,
            agent_style=test_agent_style,
            balance=real_agent_balance,
            holdings=real_agent_holdings,
            recent_activity=real_recent_activity,
        )

        # Capture prompts for JSON dump
        system_prompt = market_analyst.agent.instructions
        task_prompt = market_analyst.build_prompt(context)

        # Validate fixtures returned real seeded data (catches pipeline bugs early,
        # before expensive LLM call).
        assert len(real_agent_holdings) >= 2, "Expected seeded holdings (AAPL + MSFT)"
        assert real_agent_balance > 0, "Expected positive seeded balance"

        logger.info("Running Market Analyst...")

        # Run agent - returns AgentRunResult with tool_calls and tool_errors
        # MaxTurnsExceeded can still be thrown by SDK
        try:
            result = await market_analyst.run(context, max_turns=15)
        except MaxTurnsExceeded as e:
            logger.error("=" * 60)
            logger.error("MAX TURNS EXCEEDED")
            logger.error(f"Exception: {e}")
            logger.error("=" * 60)
            raise

        # Dump result to JSON for manual inspection (always, even on failure)
        try:
            # Log tool calls from AgentRunResult
            logger.info(f"Tool calls made: {len(result.tool_calls)}")
            for tc in result.tool_calls:
                logger.info(f"  - {tc.name}: {tc.params}")

            # Portfolio context (holdings, activity) is now passed inline in
            # the prompt — no DB tool assertions needed.

            # Log tool errors but don't fail — agents skip unsupported symbols
            # and continue with other candidates. This matches production behavior.
            if result.tool_errors:
                for err in result.tool_errors:
                    logger.warning(f"TOOL ERROR (non-fatal): {err.name}: {err.output[:200]}")

            # Extract response from AgentRunResult
            response = result.output

            # Log results
            logger.info("-" * 40)
            logger.info(f"Summary: {response.summary[:200]}...")
            logger.info(f"Candidates: {response.candidates}")
            logger.info(f"Sources: {len(response.webSources)}")
            logger.info("-" * 40)

            # Structural assertions — these are deterministic guarantees from the
            # ResearchResponse model, not LLM content judgments.
            assert response is not None
            assert isinstance(response, ResearchResponse)

            # Summary should be meaningful research output
            assert isinstance(response.summary, str)
            assert len(response.summary) > 10, "Summary should be meaningful"

            # Agent should always find at least one candidate stock
            assert isinstance(response.candidates, list)
            assert len(response.candidates) >= 1, "Market Analyst should find at least one candidate"
            from models.llm_output import CandidateStock
            for candidate in response.candidates:
                assert isinstance(candidate, CandidateStock)
                assert len(candidate.symbol) >= 1, "Candidate symbol must not be empty"
                assert candidate.price > 0, "Candidate must have a positive price"

            # Research should cite at least one source
            assert len(response.webSources) >= 1, "Research should cite at least one source"
            for source in response.webSources:
                assert source.title, "Source must have a title"
                assert source.url, "Source must have a URL"

            # Portfolio context should be populated (agent must explain how portfolio influenced research)
            assert len(response.portfolio_context) > 20, "portfolio_context should explain how portfolio influenced research"

            # Agent should have made at least one tool call (brave_web_search at minimum)
            assert len(result.tool_calls) >= 1, "Market Analyst should make at least one tool call"

            # Verify brave_web_search was specifically used (core research tool)
            tool_names = [tc.name for tc in result.tool_calls]
            assert "brave_web_search" in tool_names, "MarketAnalyst should use brave_web_search for research"

            # Tool errors are expected (LLM may pick symbols Finnhub doesn't support)
            # What matters is the research output is valid despite any lookup failures

            logger.info("TEST PASSED")
        finally:
            _dump_result_to_json(
                "test_market_analyst_returns_candidates",
                result,
                system_prompt=system_prompt,
                task_prompt=task_prompt,
            )

