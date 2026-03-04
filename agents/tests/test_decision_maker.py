"""Tests for Decision Maker agent (two-agent architecture).

The Decision Maker is the second agent in the two-agent flow:
- Receives research results from Market Analyst
- Has database tools (get_symbol_trade_history)
- Account data is passed inline in the decision prompt
- Uses structured output (TradingDecision) instead of tool callback
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from decision_maker import create_decision_maker_agent, build_decision_prompt
from models import Holding
from models.llm_output import TradingDecision


@pytest.mark.asyncio
class TestDecisionMakerAgent:
    """Test Decision Maker agent creation and configuration."""

    async def test_create_agent_with_trading_tools(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_model_name,
        mock_mcp_pool,
    ):
        """Test Decision Maker is created with proper configuration."""
        # Create Decision Maker (new API: agent_id instead of executor)
        agent = await create_decision_maker_agent(
            agent_name=sample_agent_name,
            agent_id=sample_agent_id,
            mcp_pool=mock_mcp_pool,
            model_name=sample_model_name,
        )

        # Verify agent created
        assert agent is not None
        assert agent.name == f"{sample_agent_name}-DecisionMaker"
        # Verify structured output type is TradingDecision
        assert agent.output_type == TradingDecision

    async def test_create_agent_without_mcp_pool(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_model_name,
    ):
        """Test MCP pool is optional."""
        # Create Decision Maker with no MCP pool
        agent = await create_decision_maker_agent(
            agent_name=sample_agent_name,
            agent_id=sample_agent_id,
            mcp_pool=None,  # No MCP servers
            model_name=sample_model_name,
        )

        # Verify agent still created successfully
        assert agent is not None
        assert agent.output_type == TradingDecision


@pytest.mark.asyncio
class TestBuildDecisionPrompt:
    """Test decision prompt generation."""

    def test_prompt_includes_research_results(
        self, sample_research_response
    ):
        """Test prompt includes Market Analyst candidates and sources."""
        prompt = build_decision_prompt(
            research_response=sample_research_response,
            balance=100000.0,
            position_count=3,
            max_positions=10,
            holdings_summary="AAPL: 100 shares",
            historical_context="{}",
            force_trade=False,
        )

        # Verify prompt structure
        assert isinstance(prompt, str)
        assert len(prompt) > 0

        # Verify research results included
        assert sample_research_response.summary in prompt
        assert len(sample_research_response.sources) > 0
        # At least one source should be mentioned
        assert any(source.title in prompt for source in sample_research_response.sources)

    def test_prompt_includes_force_trade_flag(
        self, sample_research_response
    ):
        """Test force_trade appears in prompt when True."""
        prompt_with_force = build_decision_prompt(
            research_response=sample_research_response,
            balance=100000.0,
            position_count=5,
            max_positions=10,
            holdings_summary="Diversified",
            historical_context="{}",
            force_trade=True,
        )

        prompt_without_force = build_decision_prompt(
            research_response=sample_research_response,
            balance=100000.0,
            position_count=5,
            max_positions=10,
            holdings_summary="Diversified",
            historical_context="{}",
            force_trade=False,
        )

        # Verify prompts are different
        assert prompt_with_force != prompt_without_force

        # Verify force_trade mentioned
        assert "must" in prompt_with_force.lower() or "force" in prompt_with_force.lower()

    def test_prompt_includes_position_limit_warning(
        self, sample_research_response
    ):
        """Test prompt warns when at 10 position limit."""
        prompt_at_limit = build_decision_prompt(
            research_response=sample_research_response,
            balance=100000.0,
            position_count=10,  # At limit
            max_positions=10,
            holdings_summary="10 positions",
            historical_context="{}",
            force_trade=False,
        )

        prompt_not_at_limit = build_decision_prompt(
            research_response=sample_research_response,
            balance=100000.0,
            position_count=5,  # Not at limit
            max_positions=10,
            holdings_summary="5 positions",
            historical_context="{}",
            force_trade=False,
        )

        # Verify prompts are different
        assert prompt_at_limit != prompt_not_at_limit

        # Verify warning for at-limit case
        assert "10" in prompt_at_limit
        assert "limit" in prompt_at_limit.lower() or "maximum" in prompt_at_limit.lower() or "cannot buy" in prompt_at_limit.lower()

    def test_prompt_includes_balance_and_holdings(
        self, sample_research_response
    ):
        """Test prompt includes current balance and holdings."""
        holdings_summary = "AAPL: 100 shares @ $150.00, MSFT: 50 shares @ $300.00"
        prompt = build_decision_prompt(
            research_response=sample_research_response,
            balance=100000.0,
            position_count=2,
            max_positions=10,
            holdings_summary=holdings_summary,
            historical_context="{}",
            force_trade=False,
        )

        # Verify balance included
        assert "$100,000" in prompt or "100000" in prompt

        # Verify holdings included
        assert "AAPL" in prompt
        assert "MSFT" in prompt
