"""Tests for Decision Maker agent (two-agent architecture).

The Decision Maker is the second agent in the two-agent flow:
- Receives research results from Market Analyst
- Has database tools (get_symbol_trade_history)
- Account data is passed inline in the decision prompt
- Uses structured output (TradingDecision) instead of tool callback
"""

import pytest

from ai_agents.decision_maker import create_decision_maker_agent, build_decision_prompt
from models import Holding
from models.llm_output import TradingDecision


@pytest.mark.asyncio
class TestDecisionMakerAgent:
    """Test Decision Maker agent creation and configuration."""

    @pytest.mark.usefixtures('mock_prompt_fetch')
    async def test_create_agent_with_trading_tools(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_model_name,
        mock_mcp_pool,
    ):
        """Test Decision Maker is created with proper configuration."""
        agent = await create_decision_maker_agent(
            agent_name=sample_agent_name,
            agent_id=sample_agent_id,
            mcp_pool=mock_mcp_pool,
            model_name=sample_model_name,
        )

        assert agent is not None
        assert agent.name == f"{sample_agent_name}-DecisionMaker"
        assert agent.output_type == TradingDecision


class TestBuildDecisionPrompt:
    """Test decision prompt generation."""

    def test_prompt_includes_position_limit_warning(
        self, sample_research_response
    ):
        """Test prompt warns when at 10 position limit."""
        prompt_at_limit = build_decision_prompt(
            research_response=sample_research_response,
            balance=100000.0,
            position_count=10,
            max_positions=10,
            holdings_summary="10 positions",
            historical_context="{}",
            force_trade=False,
        )

        prompt_not_at_limit = build_decision_prompt(
            research_response=sample_research_response,
            balance=100000.0,
            position_count=5,
            max_positions=10,
            holdings_summary="5 positions",
            historical_context="{}",
            force_trade=False,
        )

        assert prompt_at_limit != prompt_not_at_limit
        assert "10" in prompt_at_limit
        assert "limit" in prompt_at_limit.lower() or "maximum" in prompt_at_limit.lower() or "cannot buy" in prompt_at_limit.lower()
