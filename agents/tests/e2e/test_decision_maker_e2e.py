"""E2E smoke test for Decision Maker with real integrations.

Run with: pytest tests/e2e/test_decision_maker_e2e.py -v -s

WARNING: This test costs real $ (OpenAI). Run sparingly.
"""

import logging
import pytest

from decision_maker import DecisionMaker, DecisionContext
from models.llm_output import TradingDecision, ResearchResponse, ResearchSource
from agents import Runner

logger = logging.getLogger("e2e_tests.decision_maker")


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.costly
class TestDecisionMakerE2E:
    """E2E smoke test for Decision Maker."""

    @pytest.mark.asyncio
    async def test_decision_maker_returns_valid_decision(
        self,
        test_agent_id,
        test_agent_name,
        test_agent_style,
        test_model_name,
        sample_holdings,
        sample_recent_activity,
    ):
        """Smoke test: Decision Maker returns a valid trading decision.

        Verifies:
        1. Real OpenAI API call works
        2. Returns valid TradingDecision (BUY/SELL/HOLD)
        3. Decision has required fields populated
        """
        logger.info("=" * 60)
        logger.info("E2E SMOKE TEST: Decision Maker")
        logger.info("=" * 60)
        logger.info(f"Agent: {test_agent_name} ({test_agent_style})")

        # Create Decision Maker using async factory (no MCP needed for decision phase)
        decision_maker = await DecisionMaker.create(
            agent_name=test_agent_name,
            agent_id=test_agent_id,
            mcp_pool=None,  # Decision Maker doesn't need MCP
            model_name=test_model_name,
        )

        # Sample research response (simulates Market Analyst output)
        research_response = ResearchResponse(
            summary="Found 3 value stocks with strong fundamentals. JPM has P/E of 12, solid dividend.",
            candidates=["JPM", "BAC", "WFC"],
            sources=[
                ResearchSource(title="JPMorgan Analysis", url="https://example.com/jpm"),
            ]
        )

        # Build context and prompt
        context = DecisionContext(
            agent_name=test_agent_name,
            agent_style=test_agent_style,
            research_response=research_response,
            balance=50000.0,
            holdings=sample_holdings,
            recent_activity=sample_recent_activity,
            force_trade=False,
            max_positions=10,
        )
        prompt = decision_maker.build_prompt(context)

        logger.info("Running Decision Maker...")

        # Run agent with real LLM
        result = await Runner.run(decision_maker.agent, prompt, max_turns=30)

        # Extract decision
        decision = result.final_output_as(TradingDecision)

        # Log results
        logger.info("-" * 40)
        logger.info(f"Action: {decision.action}")
        logger.info(f"Symbol: {decision.symbol}")
        logger.info(f"Quantity: {decision.quantity}")
        logger.info(f"Rationale: {decision.rationale[:100]}...")
        logger.info("-" * 40)

        # Assertions - structure only (LLM output is non-deterministic)
        assert decision is not None
        assert isinstance(decision, TradingDecision)
        assert decision.action in ["BUY", "SELL", "HOLD"]

        if decision.action in ["BUY", "SELL"]:
            assert decision.symbol is not None
            assert decision.quantity is not None
            assert decision.quantity > 0

        assert isinstance(decision.rationale, str)
        assert len(decision.rationale) > 5

        logger.info("TEST PASSED")
