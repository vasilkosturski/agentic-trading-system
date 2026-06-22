"""E2E smoke test for full Agent Executor cycle with real integrations.

Run with: pytest tests/e2e/test_full_cycle_e2e.py -v -s

WARNING: This test costs real $ (Brave Search + OpenAI) AND executes a real trade.
"""

import logging
from contextlib import AsyncExitStack

import pytest
import requests
from agents.mcp import MCPServerStdio

from mcp_helpers.params import get_mcp_server_params
from mcp_helpers.types import MCPPool
from models import TradeAction
from phase_runner import run_cycle

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
def real_agent_identity(test_agent_id, test_agent_name, test_agent_style, test_model_name):
    """Agent-identity bundle used by the e2e cycle invocation."""
    return {
        "agent_id": test_agent_id,
        "name": test_agent_name,
        "agent_style": test_agent_style,
        "model_name": test_model_name,
    }


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.costly
@pytest.mark.usefixtures("require_openai_api_key", "require_brave_api_key", "require_backend")
class TestFullCycleE2E:
    """E2E smoke test for complete trading cycle."""

    @pytest.mark.asyncio
    async def test_full_cycle_executes_trade(
        self,
        real_agent_identity: dict,
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
        logger.info(f"Agent: {real_agent_identity['name']} ({real_agent_identity['agent_style']})")

        backend_url = require_backend
        agent_id = real_agent_identity["agent_id"]

        # Baseline: capture the most recent run-id for this agent BEFORE the
        # cycle so we can identify the cycle's row afterwards. ``run_cycle``
        # is fire-and-forget (no return value); the backend DB is the source
        # of truth for what happened.
        latest_before = requests.get(
            f"{backend_url}/api/runs", params={"agentId": agent_id, "limit": 1}, timeout=10
        )
        latest_before.raise_for_status()
        before_runs = latest_before.json().get("runs") or latest_before.json()
        baseline_run_id = before_runs[0]["runId"] if before_runs else 0

        # Execute full cycle with forced trade
        await run_cycle(
            **real_agent_identity,
            mcp_pool=real_mcp_pool,
            force_trade=True,  # Ensures BUY or SELL (no HOLD)
        )

        # Pick up the cycle's new run-id from the backend.
        latest_after = requests.get(
            f"{backend_url}/api/runs", params={"agentId": agent_id, "limit": 1}, timeout=10
        )
        latest_after.raise_for_status()
        after_runs = latest_after.json().get("runs") or latest_after.json()
        assert after_runs, "Backend returned no runs after the cycle"
        run_id = after_runs[0]["runId"]
        assert (
            run_id > baseline_run_id
        ), f"Cycle did not create a new run (baseline={baseline_run_id}, latest={run_id})"

        # =================================================================
        # Phase-based API verification
        # Verify the full data pipeline round-tripped through the database
        # =================================================================
        logger.info("=" * 60)
        logger.info(f"VERIFYING PHASE-BASED APIs (run_id={run_id})")
        logger.info("=" * 60)

        # GET /api/runs/{run_id} — complete run with all phases
        resp = requests.get(f"{backend_url}/api/runs/{run_id}", timeout=10)
        assert resp.status_code == 200, f"GET /api/runs/{run_id} returned {resp.status_code}"
        run_detail = resp.json()

        # --- Run metadata ---
        run_meta = run_detail["run"]
        assert run_meta["runId"] == run_id
        assert run_meta["status"] == "COMPLETED"
        assert run_meta["phase"] == "COMPLETED"
        # With force_trade=True, must be BUY or SELL.
        assert run_meta["decision"] in (
            TradeAction.BUY.value,
            TradeAction.SELL.value,
        ), f"Expected BUY/SELL with force_trade, got {run_meta['decision']}"
        symbol = run_meta["symbol"]
        assert symbol is not None
        # Allow dots for class shares (e.g., BRK.B, BF.B).
        symbol_clean = symbol.replace(".", "")
        assert symbol_clean.isalpha(), f"Symbol should be alphabetic (dots allowed): {symbol}"
        assert symbol.isupper(), f"Symbol should be uppercase: {symbol}"
        assert 1 <= len(symbol) <= 6, f"Symbol length should be 1-6: {symbol}"
        logger.info(
            f"  Run metadata: OK (status={run_meta['status']}, decision={run_meta['decision']}, symbol={symbol})"
        )

        # --- Research phase ---
        research = run_detail["research"]
        assert research is not None, "Research phase should be present"
        assert research["runId"] == run_id
        assert isinstance(research["candidates"], list)
        assert len(research["candidates"]) > 0, "Should have research candidates"
        if research.get("sources"):
            for source in research["sources"]:
                assert "type" in source, "Source must have a type"
        logger.info(f"  Research: OK (candidates={research['candidates']})")

        # --- Decision phase ---
        decision = run_detail["decision"]
        assert decision is not None, "Decision phase should be present"
        assert decision["runId"] == run_id
        assert decision["decision"] == run_meta["decision"]
        assert decision["symbol"] == symbol
        assert decision["quantity"] is not None and decision["quantity"] > 0

        # Structured reasoning (3 fields)
        reasoning = decision.get("reasoning")
        if reasoning is not None:
            for field in ("portfolioContext", "historicalContext", "researchContext"):
                assert field in reasoning, f"Reasoning missing field: {field}"
            logger.info("  Decision reasoning: OK (all 3 fields present)")
        logger.info(f"  Decision: OK (action={decision['decision']}, symbol={decision['symbol']})")

        # --- Execution phase ---
        execution = run_detail.get("execution")
        assert execution is not None, "Execution phase should be present for BUY/SELL"
        assert execution["runId"] == run_id
        assert execution["status"] in ["COMPLETED", "FAILED"]
        logger.info(f"  Execution: OK (status={execution['status']})")

        logger.info("=" * 60)
        logger.info("PHASE-BASED API VERIFICATION PASSED")
        logger.info("=" * 60)

        logger.info("TEST PASSED")
