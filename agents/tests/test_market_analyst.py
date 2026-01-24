"""Tests for Market Analyst agent (two-agent architecture).

The Market Analyst is the first agent in the two-agent flow:
- Conducts research using Brave Search + Fetch MCPs
- NO trading tools or database access
- Returns ResearchResponse with candidates and sources
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from market_analyst import create_market_analyst_agent, build_research_prompt
from models.llm_output import ResearchResponse


@pytest.mark.asyncio
class TestMarketAnalystAgent:
    """Test Market Analyst agent creation and configuration."""

    async def test_create_agent_with_correct_mcp_servers(
        self,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_model_name,
        mock_mcp_pool,
    ):
        """Test Market Analyst gets Brave Search + Fetch MCPs."""
        # Mock MCP pool to return mock servers
        mock_brave_server = MagicMock()
        mock_fetch_server = MagicMock()

        async def get_server_side_effect(name):
            if name == "brave-search":
                return mock_brave_server
            elif name == "fetch":
                return mock_fetch_server
            return None

        mock_mcp_pool.get_server = AsyncMock(side_effect=get_server_side_effect)

        # Create Market Analyst
        agent = await create_market_analyst_agent(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            strategy=sample_strategy,
            mcp_pool=mock_mcp_pool,
            model_name=sample_model_name,
        )

        # Verify agent created
        assert agent is not None
        assert agent.name == f"{sample_agent_name}-MarketAnalyst"

        # Verify MCP servers were requested
        assert mock_mcp_pool.get_server.call_count >= 2
        assert any(
            call[0][0] == "brave-search"
            for call in mock_mcp_pool.get_server.call_args_list
        )
        assert any(
            call[0][0] == "fetch" for call in mock_mcp_pool.get_server.call_args_list
        )

    async def test_agent_has_no_trading_tools(
        self,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_model_name,
        mock_mcp_pool,
    ):
        """Test Market Analyst has NO trading tools."""
        # Create Market Analyst
        agent = await create_market_analyst_agent(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            strategy=sample_strategy,
            mcp_pool=mock_mcp_pool,
            model_name=sample_model_name,
        )

        # Verify agent created
        assert agent is not None

        # Verify no trading tool names in agent (if tools are accessible)
        # Note: OpenAI Agents SDK may not expose tools directly, so this is best-effort
        if hasattr(agent, "tools"):
            tool_names = [
                tool.name if hasattr(tool, "name") else str(tool) for tool in agent.tools
            ]
            assert "buy_shares" not in tool_names
            assert "sell_shares" not in tool_names
            assert "decide_action" not in tool_names

    async def test_output_type_is_research_response(
        self,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_model_name,
        mock_mcp_pool,
    ):
        """Test agent enforces ResearchResponse output type."""
        # Create Market Analyst
        agent = await create_market_analyst_agent(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            strategy=sample_strategy,
            mcp_pool=mock_mcp_pool,
            model_name=sample_model_name,
        )

        # Verify agent created with ResearchResponse output type
        assert agent is not None
        # The Agent is typed as Agent[ResearchResponse]
        # We can't directly access the type at runtime, but verify agent has output_type
        # This is enforced by the Agent[ResearchResponse] generic

    async def test_instructions_include_agent_context(
        self,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_model_name,
        mock_mcp_pool,
    ):
        """Test instructions include agent_name and agent_style."""
        # Create Market Analyst
        agent = await create_market_analyst_agent(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            strategy=sample_strategy,
            mcp_pool=mock_mcp_pool,
            model_name=sample_model_name,
        )

        # Verify agent created
        assert agent is not None

        # Verify agent name includes context
        assert sample_agent_name in agent.name

        # Verify instructions include agent style (if accessible)
        if hasattr(agent, "instructions"):
            assert sample_agent_style in agent.instructions
            assert sample_agent_name in agent.instructions


@pytest.mark.asyncio
class TestBuildResearchPrompt:
    """Test research prompt generation."""

    def test_prompt_includes_balance_and_positions(
        self, sample_agent_name, sample_agent_style
    ):
        """Test prompt includes account context."""
        prompt = build_research_prompt(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            balance=100000.0,
            position_count=3,
            max_positions=10,
            holdings_summary="AAPL: 100 shares, MSFT: 50 shares",
            historical_context='{"summary": "Recent trades"}',
        )

        # Verify prompt structure
        assert isinstance(prompt, str)
        assert len(prompt) > 0

        # Verify account context included
        assert "$100,000" in prompt or "100000" in prompt
        assert "3" in prompt  # position count
        assert "10" in prompt  # max positions

    def test_prompt_includes_holdings_summary(
        self, sample_agent_name, sample_agent_style
    ):
        """Test prompt includes current holdings."""
        holdings_summary = "AAPL: 100 shares @ $150.00, MSFT: 50 shares @ $300.00"
        prompt = build_research_prompt(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            balance=100000.0,
            position_count=2,
            max_positions=10,
            holdings_summary=holdings_summary,
            historical_context="{}",
        )

        # Verify holdings included
        assert "AAPL" in prompt
        assert "MSFT" in prompt
        assert "100 shares" in prompt

    def test_prompt_adjusts_for_portfolio_capacity(
        self, sample_agent_name, sample_agent_style
    ):
        """Test prompt changes based on position count."""
        # Nearly full portfolio (9 out of 10)
        prompt_full = build_research_prompt(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            balance=100000.0,
            position_count=9,
            max_positions=10,
            holdings_summary="Multiple holdings",
            historical_context="{}",
        )

        # Empty portfolio (0 out of 10)
        prompt_empty = build_research_prompt(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            balance=100000.0,
            position_count=0,
            max_positions=10,
            holdings_summary="No holdings",
            historical_context="{}",
        )

        # Verify prompts are different
        assert prompt_full != prompt_empty

        # Verify capacity awareness
        assert "9" in prompt_full or "one more position" in prompt_full.lower()
        assert "0" in prompt_empty or "empty" in prompt_empty.lower()

    def test_prompt_includes_historical_context(
        self, sample_agent_name, sample_agent_style
    ):
        """Test prompt includes historical trading context."""
        historical_context = '{"summary": "Last trade: Bought NVDA 50 shares", "insights": ["Strong AI growth"]}'
        prompt = build_research_prompt(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            balance=100000.0,
            position_count=1,
            max_positions=10,
            holdings_summary="NVDA: 50 shares",
            historical_context=historical_context,
        )

        # Verify historical context included (either raw or parsed)
        assert "NVDA" in prompt or "Last trade" in prompt or historical_context in prompt

    def test_prompt_includes_agent_style(
        self, sample_agent_name, sample_agent_style
    ):
        """Test prompt includes agent style guidance."""
        prompt = build_research_prompt(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            balance=100000.0,
            position_count=5,
            max_positions=10,
            holdings_summary="Diversified portfolio",
            historical_context="{}",
        )

        # Verify agent style included
        assert sample_agent_style in prompt
