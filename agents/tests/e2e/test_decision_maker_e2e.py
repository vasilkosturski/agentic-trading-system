"""E2E smoke test for Decision Maker with real integrations.

Run with: pytest tests/e2e/test_decision_maker_e2e.py -v -s

WARNING: This test costs real $ (Brave Search + OpenAI). Run sparingly.
"""

import json
import logging
from contextlib import AsyncExitStack
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import pytest
from agents import Runner
from agents.mcp import MCPServerStdio

from decision_maker import DecisionMaker, DecisionContext
from models.llm_output import TradeAction, TradingDecision, ResearchResponse, ResearchSource
from mcp_types import MCPPool
from mcp_params import get_mcp_server_params
from utils.sdk_parser import extract_tool_calls

logger = logging.getLogger("e2e_tests.decision_maker")

_RESULTS_DIR = Path(__file__).parent / "results"


def _dump_result_to_json(
    test_name: str,
    decision: TradingDecision,
    tool_calls: list,
    system_prompt: str,
    runtime_prompt: str,
) -> None:
    """Serialize DecisionMaker result to JSON for manual inspection.

    Writes to tests/e2e/results/{test_name}_{timestamp}.json.
    Silently logs on failure -- must never mask the real test outcome.
    """
    try:
        _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"{test_name}_{ts}.json"

        data = {
            "test_name": test_name,
            "timestamp": ts,
            "system_prompt": system_prompt,
            "runtime_prompt": runtime_prompt,
            "output": decision.model_dump() if decision else None,
            "tool_calls": [asdict(tc) for tc in tool_calls],
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
class TestDecisionMakerE2E:
    """E2E smoke test for Decision Maker."""

    @pytest.mark.asyncio
    async def test_decision_maker_returns_valid_decision(
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
        """Smoke test: Decision Maker returns a valid trading decision.

        Verifies:
        1. Real OpenAI API call works
        2. Real Brave Search + Fetch MCP servers are available
        3. Returns valid TradingDecision (BUY/SELL/HOLD)
        4. Decision has required fields populated
        5. Uses real backend data (seeded agent, holdings, activity)
        """
        logger.info("=" * 60)
        logger.info("E2E SMOKE TEST: Decision Maker")
        logger.info("=" * 60)
        logger.info(f"Agent: {test_agent_name} ({test_agent_style})")
        logger.info(f"Balance: {real_agent_balance}")
        logger.info(f"Holdings: {len(real_agent_holdings)} positions")

        # Create Decision Maker with real MCP pool (Brave Search + Fetch)
        decision_maker = await DecisionMaker.create(
            agent_name=test_agent_name,
            agent_id=test_agent_id,
            mcp_pool=real_mcp_pool,
            model_name=test_model_name,
        )

        # Realistic research response — includes AAPL (seeded in DB) so
        # get_symbol_trade_history returns real data for at least one candidate.
        research_response = ResearchResponse(
            summary=(
                "Identified 4 stocks with strong fundamentals. "
                "Apple (AAPL) continues strong with consistent revenue growth and P/E of 28 — consider adding to existing position. "
                "Comcast (CMCSA) has P/E of 5.81, trading below intrinsic value with strong cash flow. "
                "Allstate (ALL) offers P/E of 5.40 with robust underwriting margins. "
                "WesBanco (WSBC) priced at $36.01 vs estimated cash flow value of $68.84."
            ),
            candidates=["AAPL", "CMCSA", "ALL", "WSBC"],
            sources=[
                ResearchSource(title="Top 10 Most Undervalued Stocks in the S&P 500", url="https://www.nerdwallet.com/investing/learn/undervalued-stocks"),
                ResearchSource(title="February 2026's Value Picks: Stocks Priced Below Estimated Worth", url="https://finance.yahoo.com/news/february-2026s-value-picks-stocks-113805029.html"),
            ],
            portfolio_context="Current portfolio holds AAPL and MSFT. AAPL already held — could add to position. Other candidates diversify into financials to reduce tech concentration.",
        )

        # Build context and prompt using real backend data
        context = DecisionContext(
            agent_name=test_agent_name,
            agent_style=test_agent_style,
            research_response=research_response,
            balance=real_agent_balance,
            holdings=real_agent_holdings,
            recent_activity=real_recent_activity,
            force_trade=False,
            max_positions=10,
        )
        prompt = decision_maker.build_prompt(context)

        # Capture prompts for JSON dump
        system_prompt = decision_maker.agent.instructions
        runtime_prompt = prompt

        logger.info("Running Decision Maker...")

        # Run agent with real LLM
        result = await Runner.run(decision_maker.agent, prompt, max_turns=30)

        # Extract decision and tool calls
        decision = result.final_output_as(TradingDecision)
        tool_calls = extract_tool_calls(result.new_items)

        # ALL tool errors are fatal — backend should never return errors for valid requests
        tool_errors = [tc for tc in tool_calls if tc.is_error]
        if tool_errors:
            for err in tool_errors:
                logger.error(f"TOOL ERROR: {err.name}: {err.error_message[:200]}")

        # Dump result to JSON for manual inspection (always, even on failure)
        try:
            # Log results
            logger.info("-" * 40)
            logger.info(f"Action: {decision.action}")
            logger.info(f"Symbol: {decision.symbol}")
            logger.info(f"Quantity: {decision.quantity}")
            logger.info(f"Rationale: {decision.rationale[:100]}...")
            logger.info(f"Tool calls made: {len(tool_calls)}")
            for tc in tool_calls:
                logger.info(f"  - {tc.name}: {tc.params}")
            logger.info("-" * 40)

            # All tool errors are fatal
            assert not tool_errors, f"Tool errors: {[e.name for e in tool_errors]}"

            # Agent should have called get_symbol_trade_history at least once
            tool_names = [tc.name for tc in tool_calls]
            assert "get_symbol_trade_history" in tool_names, "DecisionMaker should check trade history for candidates"

            # Assertions -- structure only (LLM output is non-deterministic)
            assert decision is not None
            assert isinstance(decision, TradingDecision)

            # Decision should be BUY (given good candidates + available balance + position slots)
            assert decision.action == TradeAction.BUY, f"Expected BUY given strong candidates and available capital, got {decision.action}"

            assert decision.symbol is not None
            assert decision.quantity is not None
            assert decision.quantity > 0

            # Symbol format validation
            assert decision.symbol.isalpha(), f"Symbol should be alphabetic: {decision.symbol}"
            assert decision.symbol.isupper(), f"Symbol should be uppercase: {decision.symbol}"
            assert 1 <= len(decision.symbol) <= 5, f"Symbol length should be 1-5: {decision.symbol}"

            # Comprehensive reasoning field must be populated
            assert len(decision.reasoning) > 50, "reasoning should be comprehensive"

            # Rationale quality -- must be meaningful, not a stub
            assert isinstance(decision.rationale, str)
            assert len(decision.rationale) > 10, "Rationale should be meaningful"

            # Built-in consistency validation (action<->symbol<->quantity coherence)
            decision.validate_consistency()

            logger.info("TEST PASSED")
        finally:
            _dump_result_to_json(
                "test_decision_maker_returns_valid_decision",
                decision=decision,
                tool_calls=tool_calls,
                system_prompt=system_prompt,
                runtime_prompt=runtime_prompt,
            )
