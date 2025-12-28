"""Integration tests for researcher.py - tests agent wiring and LLM behavior.

Testing Strategy:
- Wiring tests (2 tests): Verify agent structure, pass immediately, no LLM needed
- Integration tests (4 tests): Test with OpenAI (default) or Ollama (experimental)
- Mocks external dependencies (backend API, MCPs)
- Verifies agent calls tools correctly and returns structured responses

Running tests:
# Default: Use OpenAI gpt-4o-mini (requires OPENAI_API_KEY)
pytest tests/test_researcher.py -v

# Experimental: Use local Ollama model (expects structured output failure)
USE_OLLAMA=true pytest tests/test_researcher.py -v

# Wiring tests only (no API key needed)
pytest tests/test_researcher.py::TestResearcherAgentWiring -v

Cost:
- OpenAI gpt-4o-mini: ~$0.01 per full test run
- Ollama: Free, but structured outputs don't work (known limitation)

Expected Results:
- OpenAI: All tests should PASS ✅
- Ollama: Integration tests should FAIL with structured output error ❌
"""

import os
import pytest
from typing import Union
from unittest.mock import patch, Mock, AsyncMock
from researcher import create_researcher_agent, run_researcher, REQUIRED_MCPS
from mcp_types import MCPPool, MCPName
from models import ResearchResponse
from agents import Runner, Model


def get_test_model() -> Union[str, Model]:
    """
    Get model for integration tests.

    Supports two modes via USE_OLLAMA environment variable:
    - USE_OLLAMA=false (default): OpenAI gpt-4o-mini (~$0.01/run)
    - USE_OLLAMA=true: Local Ollama llama3.2 (free, but structured outputs broken)

    Returns:
        Either string model name (OpenAI) or LitellmModel (Ollama)
    """
    use_ollama = os.getenv("USE_OLLAMA", "false").lower() == "true"

    if use_ollama:
        print("\n⚠️  Using Ollama - expect structured output failures!")
        try:
            from agents.extensions.models.litellm_model import LitellmModel
        except ImportError as e:
            raise ImportError(
                "\n"
                "❌ LitellmModel not available in OpenAI Agents SDK.\n"
                "\n"
                "Ollama integration requires agents.extensions.models.litellm_model\n"
                "Make sure you have the latest openai-agents package installed.\n"
            ) from e

        return LitellmModel(
            model="ollama/llama3.2",
            api_key="dummy"  # Ollama doesn't need key but SDK requires it
        )
    else:
        print("\n✅ Using OpenAI gpt-4o-mini (~$0.01/run)")
        return "gpt-4o-mini"

# Mark all tests in this file as integration tests (cost money, use real LLM)
pytestmark = pytest.mark.integration


class TestResearcherAgentWiring:
    """Test that agent is wired up correctly with tools."""

    @pytest.mark.asyncio
    async def test_create_researcher_agent_has_all_required_tools(self):
        """Verify agent has all 4 required tools registered."""
        mcp_pool: MCPPool = {}
        # Wiring test doesn't run LLM, just checks structure - use dummy model
        agent = await create_researcher_agent(mcp_pool, "gpt-4o-mini")

        # Verify agent is created
        assert agent is not None
        assert agent.name == "Researcher"

        # Verify all tools are registered
        tool_names = [tool.name for tool in agent.tools]
        assert "query_holdings_tool" in tool_names
        assert "query_recent_activity_tool" in tool_names
        assert "query_symbol_history_tool" in tool_names
        assert "lookup_price_tool" in tool_names

        # Should have exactly 4 tools
        assert len(agent.tools) == 4

    @pytest.mark.asyncio
    async def test_create_researcher_agent_requires_brave_search_and_fetch_mcps(self):
        """Verify agent declares required MCPs."""
        # This is a static check - no agent creation needed
        assert MCPName.BRAVE_SEARCH in REQUIRED_MCPS
        assert MCPName.FETCH in REQUIRED_MCPS
        assert len(REQUIRED_MCPS) == 2


class TestResearcherAgentIntegration:
    """Integration tests using real LLM with mocked backend."""

    @pytest.mark.asyncio
    async def test_researcher_calls_holdings_tool_with_real_llm(self):
        """Integration: Real LLM should call holdings tool when asked."""
        mcp_pool: MCPPool = {}

        # Mock backend to return production-realistic response (matches backend DTOs)
        with patch('researcher.call_backend', new_callable=AsyncMock) as mock_backend:
            # Realistic holdings response matching MemoryController structure
            mock_backend.return_value = Mock(
                status_code=200,
                text='{"agentName": "Warren", "balance": 95000.0, "holdings": [{"symbol": "AAPL", "quantity": 50, "averagePrice": 150.50}, {"symbol": "MSFT", "quantity": 30, "averagePrice": 320.75}], "positionCount": 2}'
            )

            agent = await create_researcher_agent(mcp_pool, get_test_model())

            # Use real LLM to run agent
            result = await Runner.run(
                agent,
                "What stocks does Warren currently hold?"
            )

            # Verify backend was called (LLM chose the right tool)
            assert mock_backend.called, "LLM should have called the backend via holdings tool"

            # Verify result structure
            assert isinstance(result.final_output, ResearchResponse)
            assert result.final_output.summary is not None

            # LLM should mention the stock in response
            # Note: This is non-deterministic, but highly likely
            summary_text = result.final_output.summary.lower()
            assert "aapl" in summary_text or "apple" in summary_text

    @pytest.mark.asyncio
    async def test_researcher_handles_backend_error_gracefully(self):
        """Integration: Real LLM should retry on errors until max turns.

        When backend consistently fails, LLM will retry the tool until max_turns is reached.
        This is expected behavior - the agent should exhaust retries before giving up.
        """
        mcp_pool: MCPPool = {}

        # Mock backend to return error consistently
        with patch('researcher.call_backend', new_callable=AsyncMock) as mock_backend:
            # Simulate HTTP error
            from http_client import BackendAPIError
            from agents.exceptions import MaxTurnsExceeded

            mock_backend.side_effect = BackendAPIError("Internal Server Error", status_code=500)

            agent = await create_researcher_agent(mcp_pool, get_test_model())

            # Expect MaxTurnsExceeded when tool consistently fails
            with pytest.raises(MaxTurnsExceeded):
                await Runner.run(
                    agent,
                    "What stocks does Warren currently hold?",
                    max_turns=5  # Use fewer turns for faster test
                )

            # Verify backend was called multiple times (LLM retried)
            assert mock_backend.call_count > 1, "LLM should retry failed tool calls"

    @pytest.mark.asyncio
    async def test_researcher_returns_research_response_type(self):
        """Integration: Verify agent returns proper ResearchResponse type."""
        mcp_pool: MCPPool = {}

        with patch('researcher.call_backend', new_callable=AsyncMock) as mock_backend:
            # Realistic empty holdings response (new agent with no positions)
            mock_backend.return_value = Mock(
                status_code=200,
                text='{"agentName": "Warren", "balance": 100000.0, "holdings": [], "positionCount": 0}'
            )

            agent = await create_researcher_agent(mcp_pool, get_test_model())

            # Run with query that doesn't need tools
            result = await Runner.run(
                agent,
                "What is the capital of France?"
            )

            # Should still return ResearchResponse even for simple queries
            assert isinstance(result.final_output, ResearchResponse)
            assert result.final_output.summary is not None
            assert "paris" in result.final_output.summary.lower()

    @pytest.mark.asyncio
    async def test_run_researcher_convenience_function(self):
        """Integration: Test run_researcher() convenience function."""
        mcp_pool: MCPPool = {}

        with patch('researcher.call_backend', new_callable=AsyncMock) as mock_backend:
            # Realistic holdings response for George with NVDA position
            mock_backend.return_value = Mock(
                status_code=200,
                text='{"agentName": "George", "balance": 98500.0, "holdings": [{"symbol": "NVDA", "quantity": 25, "averagePrice": 520.00}], "positionCount": 1}'
            )

            # Use the convenience function instead of creating agent manually
            result = await run_researcher(
                "What stocks does George currently hold?",
                mcp_pool,
                get_test_model()
            )

            # Should return ResearchResponse directly (not RunResponse)
            assert isinstance(result, ResearchResponse)
            assert result.summary is not None

            # LLM should mention the stock
            summary_text = result.summary.lower()
            assert "nvda" in summary_text or "nvidia" in summary_text


# Configuration for pytest
# To run only integration tests: pytest -m integration
# To skip integration tests: pytest -m "not integration"
