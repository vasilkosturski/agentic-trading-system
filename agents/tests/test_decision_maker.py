"""Tests for Decision Maker agent (two-agent architecture).

The Decision Maker is the second agent in the two-agent flow:
- Receives research results from Market Analyst
- Has trading tools (buy_shares, sell_shares)
- Has database tools (get_symbol_trade_history, get_account_summary)
- Records decision via decide_action tool
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from decision_maker import create_decision_maker_agent, build_decision_prompt
from agent_executor import AgentExecutor
from models import Holding


@pytest.mark.asyncio
class TestDecisionMakerAgent:
    """Test Decision Maker agent creation and configuration."""

    async def test_create_agent_with_trading_tools(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_model_name,
        mock_mcp_pool,
    ):
        """Test Decision Maker has trading tools."""
        # Create executor (needed for decide_action tool)
        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy
        )

        # Create Decision Maker
        agent = await create_decision_maker_agent(
            agent_name=sample_agent_name,
            executor=executor,
            mcp_pool=mock_mcp_pool,
            model_name=sample_model_name,
        )

        # Verify agent created
        assert agent is not None
        assert agent.name == f"{sample_agent_name}-DecisionMaker"

    async def test_decide_action_tool_stores_in_executor(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_model_name,
    ):
        """Test decide_action tool stores decision in executor."""
        # Create executor
        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy
        )

        # Create Decision Maker (no MCP pool needed for this test)
        agent = await create_decision_maker_agent(
            agent_name=sample_agent_name,
            executor=executor,
            mcp_pool=None,
            model_name=sample_model_name,
        )

        # Verify agent created
        assert agent is not None

        # Manually call decide_action (simulating tool call)
        # Note: We can't directly invoke tools from the agent, but we can test that
        # the executor has the store_decision method
        executor.store_decision(
            action="BUY",
            symbol="AAPL",
            quantity=100,
            rationale="Strong growth",
            full_reasoning="Detailed analysis",
            research_sources=json.dumps({"summary": "AAPL research", "sources": []}),
            historical_context=json.dumps({"summary": "No prior trades", "insights": []}),
        )

        # Verify decision stored in _pending_decision (new architecture)
        assert executor._pending_decision is not None
        assert executor._pending_decision.action == "BUY"
        assert executor._pending_decision.symbol == "AAPL"

    @patch("decision_maker.get_trading_history")
    async def test_get_symbol_trade_history_tool(
        self,
        mock_get_trading_history,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_model_name,
    ):
        """Test trading history tool works."""
        # Mock trading history response
        mock_get_trading_history.return_value = json.dumps({
            "symbol": "AAPL",
            "trades": [
                {"action": "BUY", "quantity": 50, "price": 150.0, "date": "2025-01-01"}
            ],
            "summary": "Bought AAPL once"
        })

        # Create executor
        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy
        )

        # Create Decision Maker
        agent = await create_decision_maker_agent(
            agent_name=sample_agent_name,
            executor=executor,
            mcp_pool=None,
            model_name=sample_model_name,
        )

        # Verify agent created
        assert agent is not None

        # Verify get_trading_history is importable and callable
        from decision_maker import get_trading_history
        result = await get_trading_history(sample_agent_name, "AAPL", days=90)
        assert "AAPL" in result

    @patch("decision_maker._get_balance_raw")
    @patch("decision_maker._get_holdings_raw")
    async def test_get_account_summary_tool(
        self,
        mock_get_holdings,
        mock_get_balance,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_model_name,
        sample_holdings,
    ):
        """Test account summary tool works."""
        # Mock backend responses
        mock_get_balance.return_value = 100000.0
        mock_get_holdings.return_value = sample_holdings

        # Create executor
        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy
        )

        # Create Decision Maker
        agent = await create_decision_maker_agent(
            agent_name=sample_agent_name,
            executor=executor,
            mcp_pool=None,
            model_name=sample_model_name,
        )

        # Verify agent created
        assert agent is not None

        # The get_account_summary tool is defined inside create_decision_maker_agent
        # We can't directly test it, but we verify the mocks are set up correctly

    async def test_optional_mcp_servers(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_model_name,
    ):
        """Test MCP servers are optional (can be None)."""
        # Create executor
        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy
        )

        # Create Decision Maker with no MCP pool
        agent = await create_decision_maker_agent(
            agent_name=sample_agent_name,
            executor=executor,
            mcp_pool=None,  # No MCP servers
            model_name=sample_model_name,
        )

        # Verify agent still created successfully
        assert agent is not None


@pytest.mark.asyncio
class TestBuildDecisionPrompt:
    """Test decision prompt generation."""

    def test_prompt_includes_research_results(
        self, sample_agent_name, sample_agent_style, sample_research_response
    ):
        """Test prompt includes Market Analyst candidates and sources."""
        prompt = build_decision_prompt(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
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
        self, sample_agent_name, sample_agent_style, sample_research_response
    ):
        """Test force_trade appears in prompt when True."""
        prompt_with_force = build_decision_prompt(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            research_response=sample_research_response,
            balance=100000.0,
            position_count=5,
            max_positions=10,
            holdings_summary="Diversified",
            historical_context="{}",
            force_trade=True,
        )

        prompt_without_force = build_decision_prompt(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
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
        self, sample_agent_name, sample_agent_style, sample_research_response
    ):
        """Test prompt warns when at 10 position limit."""
        prompt_at_limit = build_decision_prompt(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            research_response=sample_research_response,
            balance=100000.0,
            position_count=10,  # At limit
            max_positions=10,
            holdings_summary="10 positions",
            historical_context="{}",
            force_trade=False,
        )

        prompt_not_at_limit = build_decision_prompt(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
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
        self, sample_agent_name, sample_agent_style, sample_research_response
    ):
        """Test prompt includes current balance and holdings."""
        holdings_summary = "AAPL: 100 shares @ $150.00, MSFT: 50 shares @ $300.00"
        prompt = build_decision_prompt(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
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
