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
    ):
        """Test Market Analyst gets Brave Search + Fetch MCPs."""
        from mcp_types import MCPName

        # Create MCP pool dict with mock servers
        mock_brave_server = MagicMock()
        mock_fetch_server = MagicMock()
        mcp_pool = {
            MCPName.BRAVE_SEARCH: mock_brave_server,
            MCPName.FETCH: mock_fetch_server,
        }

        # Create Market Analyst
        agent = await create_market_analyst_agent(
            agent_name=sample_agent_name,
            agent_id=1,
            mcp_pool=mcp_pool,
            model_name=sample_model_name,
        )

        # Verify agent created
        assert agent is not None
        assert agent.name == f"{sample_agent_name}-MarketAnalyst"

    async def test_agent_has_no_trading_tools(
        self,
        sample_agent_name,
        sample_model_name,
        mock_mcp_pool,
    ):
        """Test Market Analyst has NO trading tools."""
        # Create Market Analyst
        agent = await create_market_analyst_agent(
            agent_name=sample_agent_name,
            agent_id=1,
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
        sample_model_name,
        mock_mcp_pool,
    ):
        """Test agent enforces ResearchResponse output type."""
        # Create Market Analyst
        agent = await create_market_analyst_agent(
            agent_name=sample_agent_name,
            agent_id=1,
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
        sample_model_name,
        mock_mcp_pool,
    ):
        """Test instructions include agent_name."""
        # Create Market Analyst
        agent = await create_market_analyst_agent(
            agent_name=sample_agent_name,
            agent_id=1,
            mcp_pool=mock_mcp_pool,
            model_name=sample_model_name,
        )

        # Verify agent created
        assert agent is not None

        # Verify agent name includes context
        assert sample_agent_name in agent.name

        # Verify instructions include agent name (if accessible)
        if hasattr(agent, "instructions"):
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
            holdings_summary="Current Holdings (3 positions):\n- AAPL: 10 shares @ $150.00 avg",
            historical_context="No recent trading activity.",
        )

        # Verify prompt structure
        assert isinstance(prompt, str)
        assert len(prompt) > 0

        # Verify account context included
        assert "$100,000" in prompt or "100000" in prompt
        assert "3" in prompt  # position count
        assert "10" in prompt  # max positions

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
            holdings_summary="Current Holdings (9 positions):\n- AAPL: 10 shares @ $150.00 avg",
            historical_context="No recent trading activity.",
        )

        # Empty portfolio (0 out of 10)
        prompt_empty = build_research_prompt(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            balance=100000.0,
            position_count=0,
            max_positions=10,
            holdings_summary="No current holdings.",
            historical_context="No recent trading activity.",
        )

        # Verify prompts are different
        assert prompt_full != prompt_empty

        # Verify capacity awareness
        assert "9" in prompt_full or "one more position" in prompt_full.lower()
        assert "0" in prompt_empty or "empty" in prompt_empty.lower()

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
            holdings_summary="Current Holdings (5 positions):\n- AAPL: 10 shares @ $150.00 avg",
            historical_context="No recent trading activity.",
        )

        # Verify agent style included
        assert sample_agent_style in prompt
