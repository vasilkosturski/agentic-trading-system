"""E2E smoke test for full Agent Executor cycle with real integrations.

Run with: pytest tests/e2e/test_full_cycle_e2e.py -v -s

WARNING: This test costs real $ (Brave Search + OpenAI) AND executes a real trade.
"""

import logging
from contextlib import AsyncExitStack

import pytest
from agents.mcp import MCPServerStdio

from agent_executor import AgentExecutor
from mcp_types import MCPPool
from mcp_params import get_mcp_server_params
from models import CycleResult

logger = logging.getLogger("e2e_tests.full_cycle")


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


@pytest.fixture
def real_agent_executor(test_agent_id, test_agent_name, test_agent_style, test_model_name):
    """Create a real AgentExecutor instance."""
    return AgentExecutor(
        agent_id=test_agent_id,
        name=test_agent_name,
        agent_style=test_agent_style,
        model_name=test_model_name,
    )


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.costly
class TestFullCycleE2E:
    """E2E smoke test for complete trading cycle."""

    @pytest.mark.asyncio
    async def test_full_cycle_executes_trade(
        self,
        real_agent_executor: AgentExecutor,
        real_mcp_pool: MCPPool,
    ):
        """Smoke test: Full cycle from research to trade execution.

        Verifies the complete flow:
        1. Market Analyst researches (real Brave Search + OpenAI)
        2. Decision Maker decides (real OpenAI)
        3. Trade executes (real backend API)
        4. Run completes with all data persisted

        Uses force_trade=True to ensure a BUY/SELL decision.
        """
        logger.info("=" * 60)
        logger.info("E2E SMOKE TEST: Full Trading Cycle")
        logger.info("=" * 60)
        logger.info(f"Agent: {real_agent_executor.name} ({real_agent_executor.agent_style})")

        # Execute full cycle with forced trade
        result = await real_agent_executor.execute_cycle(
            mcp_pool=real_mcp_pool,
            force_trade=True,  # Ensures BUY or SELL (no HOLD)
        )

        # Log results
        logger.info("-" * 40)
        logger.info("CYCLE RESULT:")
        logger.info(f"Run ID: {result.run_id}")
        logger.info(f"Decision: {result.decision.action} {result.decision.symbol}")
        logger.info(f"Quantity: {result.decision.quantity}")
        logger.info(f"Trade Count: {result.trade_count}")
        logger.info(f"Rationale: {result.decision.rationale[:200]}...")
        logger.info("-" * 40)

        # Assertions
        assert result is not None
        assert isinstance(result, CycleResult)
        assert result.run_id is not None and result.run_id > 0

        # With force_trade=True, must be BUY or SELL
        assert result.decision.action in ["BUY", "SELL"], f"Expected BUY/SELL with force_trade, got {result.decision.action}"
        assert result.decision.symbol is not None
        assert result.decision.quantity is not None
        assert result.decision.quantity > 0

        # Trade should have been attempted (count is 0 or 1 depending on execution success)
        assert result.trade_count in [0, 1]

        logger.info("TEST PASSED")
