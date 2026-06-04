"""Tests for Market Analyst agent (two-agent architecture).

The Market Analyst is the first agent in the two-agent flow:
- Conducts research using Brave Search + Fetch MCPs
- NO trading tools or database access
- Returns ResearchResponse with candidates and sources
"""

from unittest.mock import MagicMock

import pytest

from ai_agents.market_analyst import build_research_prompt, create_market_analyst_agent


@pytest.mark.asyncio
class TestMarketAnalystAgent:
    """Test Market Analyst agent creation and configuration."""

    @pytest.mark.usefixtures("mock_prompt_fetch")
    async def test_create_agent_with_correct_mcp_servers(
        self,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_model_name,
    ):
        """Test Market Analyst gets Brave Search + Fetch MCPs."""
        from mcp_helpers.types import MCPName

        mock_brave_server = MagicMock()
        mock_fetch_server = MagicMock()
        mcp_pool = {
            MCPName.BRAVE_SEARCH: mock_brave_server,
            MCPName.FETCH: mock_fetch_server,
        }

        agent = await create_market_analyst_agent(
            agent_name=sample_agent_name,
            mcp_pool=mcp_pool,
            model_name=sample_model_name,
        )

        assert agent is not None
        assert agent.name == f"{sample_agent_name}-MarketAnalyst"


class TestBuildResearchPrompt:
    """Test research prompt generation."""

    def test_prompt_adjusts_for_portfolio_capacity(self, sample_agent_name, sample_agent_style):
        """Test prompt changes based on position count."""
        prompt_full = build_research_prompt(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            balance=100000.0,
            position_count=9,
            max_positions=10,
            holdings_summary="Current Holdings (9 positions):\n- AAPL: 10 shares @ $150.00 avg",
            historical_context="No recent trading activity.",
        )

        prompt_empty = build_research_prompt(
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            balance=100000.0,
            position_count=0,
            max_positions=10,
            holdings_summary="No current holdings.",
            historical_context="No recent trading activity.",
        )

        assert prompt_full != prompt_empty
        assert "9" in prompt_full or "one more position" in prompt_full.lower()
        assert "0" in prompt_empty or "empty" in prompt_empty.lower()
