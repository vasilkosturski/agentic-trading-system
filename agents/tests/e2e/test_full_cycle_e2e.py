"""E2E smoke test for full Agent Executor cycle with real integrations.

Run with: pytest tests/e2e/test_full_cycle_e2e.py -v -s

WARNING: This test costs real $ (Brave Search + OpenAI) AND executes a real trade.
"""

import logging
from contextlib import AsyncExitStack

import pytest
import requests
from agents.mcp import MCPServerStdio

from agent_executor import AgentExecutor
from mcp_types import MCPPool
from mcp_params import get_mcp_server_params
from models import CycleResult, TradeAction

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
@pytest.mark.usefixtures("require_openai_api_key", "require_brave_api_key", "require_backend")
class TestFullCycleE2E:
    """E2E smoke test for complete trading cycle."""

    @pytest.mark.asyncio
    async def test_full_cycle_executes_trade(
        self,
        real_agent_executor: AgentExecutor,
        real_mcp_pool: MCPPool,
        require_backend: str,
    ):
        """Smoke test: Full cycle from research to trade execution.

        Verifies the complete flow:
        1. Market Analyst researches (real Brave Search + OpenAI)
        2. Decision Maker decides (real OpenAI)
        3. Trade executes (real backend API)
        4. Run completes with all data persisted
        5. Phase-based APIs return correct structured data

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

        # Assertions on in-memory result
        assert result is not None
        assert isinstance(result, CycleResult)
        assert result.run_id is not None and result.run_id > 0

        # With force_trade=True, must be BUY or SELL
        assert result.decision.action in (TradeAction.BUY, TradeAction.SELL), f"Expected BUY/SELL with force_trade, got {result.decision.action}"
        assert result.decision.symbol is not None
        assert result.decision.quantity is not None
        assert result.decision.quantity > 0

        # Structural assertions on decision quality — deterministic guarantees
        # from the TradingDecision model, not LLM content judgments.
        assert len(result.decision.rationale) > 10, "Rationale should be meaningful"
        result.decision.validate_consistency()  # Validates action↔symbol↔quantity coherence

        # Symbol format (BUY/SELL guaranteed by force_trade)
        assert result.decision.symbol.isalpha(), f"Symbol should be alphabetic: {result.decision.symbol}"
        assert result.decision.symbol.isupper(), f"Symbol should be uppercase: {result.decision.symbol}"
        assert 1 <= len(result.decision.symbol) <= 5, f"Symbol length should be 1-5: {result.decision.symbol}"

        # Structured reasoning fields should be populated for trade decisions
        assert len(result.decision.portfolioContext) > 0, "portfolioContext should be populated for BUY/SELL"
        assert len(result.decision.researchContext) > 0, "researchContext should be populated for BUY/SELL"

        # Trade should have been attempted (count is 0 or 1 depending on execution success)
        assert result.trade_count in [0, 1]

        # =================================================================
        # Phase-based API verification
        # Verify the full data pipeline round-tripped through the database
        # =================================================================
        logger.info("=" * 60)
        logger.info("VERIFYING PHASE-BASED APIs")
        logger.info("=" * 60)

        backend_url = require_backend
        run_id = result.run_id

        # GET /api/runs/{run_id} — complete run with all phases
        resp = requests.get(f"{backend_url}/api/runs/{run_id}", timeout=10)
        assert resp.status_code == 200, f"GET /api/runs/{run_id} returned {resp.status_code}"
        run_detail = resp.json()

        # --- Run metadata ---
        run_meta = run_detail["run"]
        assert run_meta["runId"] == run_id
        assert run_meta["status"] == "COMPLETED"
        assert run_meta["phase"] == "COMPLETED"
        assert run_meta["decision"] == result.decision.action
        assert run_meta["symbol"] == result.decision.symbol
        logger.info(f"  Run metadata: OK (status={run_meta['status']}, decision={run_meta['decision']})")

        # --- Research phase ---
        research = run_detail["research"]
        assert research is not None, "Research phase should be present"
        assert research["runId"] == run_id
        assert isinstance(research["candidates"], list)
        assert len(research["candidates"]) > 0, "Should have research candidates"
        if research.get("webSources"):
            for source in research["webSources"]:
                assert "type" in source, "Source must have a type"
        logger.info(f"  Research: OK (candidates={research['candidates']})")

        # --- Decision phase ---
        decision = run_detail["decision"]
        assert decision is not None, "Decision phase should be present"
        assert decision["runId"] == run_id
        assert decision["decision"] == result.decision.action
        assert decision["symbol"] == result.decision.symbol
        assert decision["quantity"] == result.decision.quantity

        # Structured reasoning (3 fields)
        reasoning = decision.get("reasoning")
        if reasoning is not None:
            reasoning_fields = [
                "portfolioContext", "historicalContext", "researchContext",
            ]
            for field in reasoning_fields:
                assert field in reasoning, f"Reasoning missing field: {field}"
            logger.info(f"  Decision reasoning: OK (all 3 fields present)")

        logger.info(f"  Decision: OK (action={decision['decision']}, symbol={decision['symbol']})")

        # --- Execution phase ---
        execution = run_detail.get("execution")
        if result.decision.action in (TradeAction.BUY, TradeAction.SELL):
            assert execution is not None, "Execution phase should be present for BUY/SELL"
            assert execution["runId"] == run_id
            assert execution["status"] in ["COMPLETED", "FAILED"]
            logger.info(f"  Execution: OK (status={execution['status']})")

        logger.info("=" * 60)
        logger.info("PHASE-BASED API VERIFICATION PASSED")
        logger.info("=" * 60)

        logger.info("TEST PASSED")
