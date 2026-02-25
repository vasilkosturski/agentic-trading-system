"""E2E smoke test for Market Analyst with real integrations.

Run with: pytest tests/e2e/test_market_analyst_e2e.py -v -s

WARNING: This test costs real $ (Brave Search + OpenAI). Run sparingly.
"""

import logging
from contextlib import AsyncExitStack

import pytest
from agents.mcp import MCPServerStdio
from agents.exceptions import MaxTurnsExceeded

from market_analyst import MarketAnalyst, MarketAnalystContext
from mcp_types import MCPPool
from mcp_params import get_mcp_server_params
from models.llm_output import ResearchResponse

logger = logging.getLogger("e2e_tests.market_analyst")


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

        # Log tool calls from AgentRunResult
        logger.info(f"Tool calls made: {len(result.tool_calls)}")
        for tc in result.tool_calls:
            logger.info(f"  - {tc.name}: {tc.params}")

        # Agent should use portfolio context tools (query_holdings_tool and/or
        # query_recent_activity_tool) — not just web search.
        db_tool_names = {"query_holdings_tool", "query_recent_activity_tool"}
        db_tool_calls = [tc for tc in result.tool_calls if tc.name in db_tool_names]
        assert len(db_tool_calls) >= 1, (
            f"Market Analyst should call at least one DB tool {db_tool_names}, "
            f"but only called: {[tc.name for tc in result.tool_calls]}"
        )

        # ALL tool errors are fatal — the E2E test validates the full pipeline
        # including external integrations (Brave Search, Fetch).
        # If external services are flaky, fix retry logic in the tools themselves.
        if result.tool_errors:
            logger.error("=" * 60)
            logger.error("TOOL ERRORS (fatal)")
            logger.error("=" * 60)
            for err in result.tool_errors:
                logger.error(f"  - {err.name}: {err.output[:200]}")
            logger.error("=" * 60)
            from exceptions import ToolExecutionError
            raise ToolExecutionError(
                f"Tools failed: {[e.name for e in result.tool_errors]}",
                tool_errors=result.tool_errors
            )

        # Extract response from AgentRunResult
        response = result.output

        # Log results
        logger.info("-" * 40)
        logger.info(f"Summary: {response.summary[:200]}...")
        logger.info(f"Candidates: {response.candidates}")
        logger.info(f"Sources: {len(response.sources)}")
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
        for candidate in response.candidates:
            assert isinstance(candidate, str)
            assert len(candidate) >= 1, "Candidate symbol must not be empty"

        # Research should cite at least one source
        assert len(response.sources) >= 1, "Research should cite at least one source"
        for source in response.sources:
            assert source.title, "Source must have a title"
            assert source.url, "Source must have a URL"

        # Agent should have made at least one tool call (brave_web_search at minimum)
        assert len(result.tool_calls) >= 1, "Market Analyst should make at least one tool call"

        # No tool errors should remain (already checked above, but assert for clarity)
        assert len(result.tool_errors) == 0, f"Unexpected tool errors: {result.tool_errors}"

        logger.info("TEST PASSED")

