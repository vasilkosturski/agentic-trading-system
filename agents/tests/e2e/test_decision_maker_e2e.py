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
@pytest.mark.usefixtures("require_openai_api_key", "require_backend", "seed_test_data")
class TestDecisionMakerE2E:
    """E2E smoke test for Decision Maker."""

    @pytest.mark.asyncio
    async def test_decision_maker_returns_valid_decision(
        self,
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
        2. Returns valid TradingDecision (BUY/SELL/HOLD)
        3. Decision has required fields populated
        4. Uses real backend data (seeded agent, holdings, activity)
        """
        logger.info("=" * 60)
        logger.info("E2E SMOKE TEST: Decision Maker")
        logger.info("=" * 60)
        logger.info(f"Agent: {test_agent_name} ({test_agent_style})")
        logger.info(f"Balance: {real_agent_balance}")
        logger.info(f"Holdings: {len(real_agent_holdings)} positions")

        # Create Decision Maker using async factory (no MCP needed for decision phase)
        decision_maker = await DecisionMaker.create(
            agent_name=test_agent_name,
            agent_id=test_agent_id,
            mcp_pool=None,  # Decision Maker doesn't need MCP
            model_name=test_model_name,
        )

        # Realistic research response (simulates Market Analyst output with portfolio awareness)
        research_response = ResearchResponse(
            summary=(
                "Identified 4 undervalued stocks with strong fundamentals. "
                "Comcast (CMCSA) has P/E of 5.81, trading below intrinsic value with strong cash flow. "
                "Allstate (ALL) offers P/E of 5.40 with robust underwriting margins. "
                "Wix.com (WIX) trades at 47.7% discount to estimated fair value in growing SaaS sector. "
                "WesBanco (WSBC) priced at $36.01 vs estimated cash flow value of $68.84."
            ),
            candidates=["CMCSA", "ALL", "WIX", "WSBC"],
            sources=[
                ResearchSource(title="Top 10 Most Undervalued Stocks in the S&P 500", url="https://www.nerdwallet.com/investing/learn/undervalued-stocks"),
                ResearchSource(title="February 2026's Value Picks: Stocks Priced Below Estimated Worth", url="https://finance.yahoo.com/news/february-2026s-value-picks-stocks-113805029.html"),
            ],
            portfolio_context="Current portfolio holds AAPL and MSFT. Research focused on non-tech sectors to diversify. All 4 candidates are in financials/SaaS to reduce concentration risk.",
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

        # Assertions — structure only (LLM output is non-deterministic)
        assert decision is not None
        assert isinstance(decision, TradingDecision)

        # Decision should be BUY (given good candidates + available balance + position slots)
        assert decision.action == "BUY", f"Expected BUY given strong candidates and available capital, got {decision.action}"

        assert decision.symbol is not None
        assert decision.quantity is not None
        assert decision.quantity > 0

        # Symbol format validation
        assert decision.symbol.isalpha(), f"Symbol should be alphabetic: {decision.symbol}"
        assert decision.symbol.isupper(), f"Symbol should be uppercase: {decision.symbol}"
        assert 1 <= len(decision.symbol) <= 5, f"Symbol length should be 1-5: {decision.symbol}"

        # Structured reasoning fields must be populated
        assert len(decision.portfolioContext) > 20, "portfolioContext should explain current portfolio state"
        assert len(decision.researchSummary) > 20, "researchSummary should reference research findings"
        assert len(decision.candidateEvaluation) > 20, "candidateEvaluation should compare candidates"
        assert len(decision.finalRationale) > 50, "finalRationale should be comprehensive"

        # Rationale quality — must be meaningful, not a stub
        assert isinstance(decision.rationale, str)
        assert len(decision.rationale) > 10, "Rationale should be meaningful"

        # Built-in consistency validation (action↔symbol↔quantity coherence)
        decision.validate_consistency()

        logger.info("TEST PASSED")
