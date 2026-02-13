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
class TestMarketAnalystE2E:
    """E2E smoke test for Market Analyst."""

    @pytest.mark.asyncio
    async def test_market_analyst_returns_candidates(
        self,
        real_mcp_pool: MCPPool,
        test_agent_name,
        test_agent_style,
        test_model_name,
        sample_holdings,
        sample_recent_activity,
        openai_api_key,  # Early validation - skips test if missing/invalid
        brave_api_key,   # Early validation - skips test if missing/invalid
    ):
        """Smoke test: Market Analyst finds stock candidates.

        Verifies:
        1. Real Brave Search API call works
        2. Real OpenAI API call works
        3. Returns valid ResearchResponse with candidates

        Note: openai_api_key and brave_api_key fixtures validate keys early,
        avoiding expensive LLM calls if credentials are missing.
        """
        logger.info("=" * 60)
        logger.info("E2E SMOKE TEST: Market Analyst")
        logger.info("=" * 60)
        logger.info(f"Agent: {test_agent_name} ({test_agent_style})")

        # Create Market Analyst using async factory
        market_analyst = await MarketAnalyst.create(
            agent_name=test_agent_name,
            mcp_pool=real_mcp_pool,
            model_name=test_model_name,
        )

        # Build context
        context = MarketAnalystContext(
            agent_name=test_agent_name,
            agent_style=test_agent_style,
            balance=50000.0,
            holdings=sample_holdings,
            recent_activity=sample_recent_activity,
        )

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

        # Opt-in fail-fast: raise if any tools had errors
        # This is where we decide to stop the test on tool failures
        if result.has_errors:
            logger.error("=" * 60)
            logger.error("TOOL ERRORS DETECTED")
            logger.error("=" * 60)
            for err in result.tool_errors:
                logger.error(f"  - {err.name}: {err.output[:200]}")
            logger.error("=" * 60)
            result.raise_if_errors()  # Throws ToolExecutionError

        # Extract response from AgentRunResult
        response = result.output

        # Log results
        logger.info("-" * 40)
        logger.info(f"Summary: {response.summary[:200]}...")
        logger.info(f"Candidates: {response.candidates}")
        logger.info(f"Sources: {len(response.sources)}")
        logger.info("-" * 40)

        # Assertions - structure only (LLM output is non-deterministic)
        assert response is not None
        assert isinstance(response, ResearchResponse)
        assert isinstance(response.candidates, list)
        assert isinstance(response.summary, str)
        assert len(response.summary) > 10, "Summary should be meaningful"

        logger.info("TEST PASSED")
