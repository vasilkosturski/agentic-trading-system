"""Tests for researcher.py - public API only.

Tests cover:
- Tool error handling through agent (ToolError is part of public contract)
- System prompt configuration

Note: We don't test internal helpers like _build_research_message() because they're
implementation details. They're exercised through integration tests.
"""

import pytest
from unittest.mock import patch, MagicMock

# Only import PUBLIC API
from researcher import (
    create_researcher_agent,
    get_researcher_instructions,
)
# Only import PUBLIC return types (the contract)
from models import ToolError
from http_client import BackendAPIError
from mcp_types import MCPPool


# =============================================================================
# Test System Configuration (Public)
# =============================================================================

class TestSystemConfiguration:
    """Test public system configuration."""

    def test_get_researcher_instructions_not_empty(self):
        """Instructions should be substantial."""
        instructions = get_researcher_instructions()

        assert len(instructions) > 100
        assert "financial researcher" in instructions.lower()

    def test_get_researcher_instructions_lists_tools(self):
        """Instructions should mention available tools."""
        instructions = get_researcher_instructions()

        # Database tools
        assert "query_holdings_tool" in instructions
        assert "query_recent_activity_tool" in instructions
        assert "query_symbol_history_tool" in instructions
        assert "lookup_price_tool" in instructions

        # MCP tools
        assert "Brave Search" in instructions

        # Should NOT reference non-existent tools
        assert "knowledge graph" not in instructions.lower(), \
            "Instructions should not mention Knowledge graph (tool doesn't exist)"


# =============================================================================
# Test Tool Error Handling (via public create_researcher_agent)
# =============================================================================

class TestToolErrorHandling:
    """Test that tools return ToolError on failure (part of public contract)."""

    @pytest.mark.asyncio
    async def test_holdings_tool_returns_tool_error_on_backend_failure(self):
        """Backend errors should return ToolError, not raise."""
        mcp_pool: MCPPool = {}  # Empty pool for testing
        with patch('researcher.call_backend', side_effect=BackendAPIError("Server error", status_code=500)):
            agent = await create_researcher_agent(mcp_pool, "gpt-4o-mini")

            # Find the holdings tool
            holdings_tool = next(t for t in agent.tools if "holdings" in t.name.lower())

            # Call the tool function directly
            result = await holdings_tool.on_invoke_tool(None, '{"agent_name": "Warren"}')

            # Should return ToolError, not raise
            assert isinstance(result, ToolError)
            assert result.error_type == "api_error"

    @pytest.mark.asyncio
    async def test_holdings_tool_returns_not_found_on_404(self):
        """404 error should return ToolError with 'not_found' type."""
        mcp_pool: MCPPool = {}  # Empty pool for testing
        with patch('researcher.call_backend', side_effect=BackendAPIError("Not found", status_code=404)):
            agent = await create_researcher_agent(mcp_pool, "gpt-4o-mini")
            holdings_tool = next(t for t in agent.tools if "holdings" in t.name.lower())

            result = await holdings_tool.on_invoke_tool(None, '{"agent_name": "Unknown"}')

            assert isinstance(result, ToolError)
            assert "Agent not found" in result.error
            assert result.error_type == "not_found"

    @pytest.mark.asyncio
    async def test_holdings_tool_returns_validation_error_on_bad_data(self):
        """Invalid backend data should return ToolError with 'validation' type."""
        mock_response = MagicMock()
        mock_response.text = '{"invalid": "data"}'  # Missing required fields

        mcp_pool: MCPPool = {}  # Empty pool for testing
        with patch('researcher.call_backend', return_value=mock_response):
            agent = await create_researcher_agent(mcp_pool, "gpt-4o-mini")
            holdings_tool = next(t for t in agent.tools if "holdings" in t.name.lower())

            result = await holdings_tool.on_invoke_tool(None, '{"agent_name": "Warren"}')

            assert isinstance(result, ToolError)
            assert "Invalid data from backend" in result.error
            assert result.error_type == "validation"

    @pytest.mark.asyncio
    async def test_holdings_tool_returns_unknown_error_on_unexpected_exception(self):
        """Unexpected exceptions should return ToolError with 'unknown' type."""
        mcp_pool: MCPPool = {}  # Empty pool for testing

        # Simulate unexpected error (e.g., network timeout, connection error)
        with patch('researcher.call_backend', side_effect=RuntimeError("Network timeout")):
            agent = await create_researcher_agent(mcp_pool, "gpt-4o-mini")
            holdings_tool = next(t for t in agent.tools if "holdings" in t.name.lower())

            result = await holdings_tool.on_invoke_tool(None, '{"agent_name": "Warren"}')

            assert isinstance(result, ToolError)
            assert "Unexpected error" in result.error
            assert "Network timeout" in result.error
            assert result.error_type == "unknown"

    @pytest.mark.asyncio
    async def test_recent_activity_tool_returns_unknown_error_on_unexpected_exception(self):
        """Test catch-all error handler for recent_activity_tool."""
        mcp_pool: MCPPool = {}  # Empty pool for testing

        with patch('researcher.call_backend', side_effect=ConnectionError("Connection refused")):
            agent = await create_researcher_agent(mcp_pool, "gpt-4o-mini")
            activity_tool = next(t for t in agent.tools if "recent_activity" in t.name.lower())

            result = await activity_tool.on_invoke_tool(None, '{"agent_name": "Warren", "days": 30}')

            assert isinstance(result, ToolError)
            assert "Unexpected error" in result.error
            assert "Connection refused" in result.error
            assert result.error_type == "unknown"

    @pytest.mark.asyncio
    async def test_symbol_history_tool_returns_unknown_error_on_unexpected_exception(self):
        """Test catch-all error handler for symbol_history_tool."""
        mcp_pool: MCPPool = {}  # Empty pool for testing

        with patch('researcher.call_backend', side_effect=TimeoutError("Request timed out")):
            agent = await create_researcher_agent(mcp_pool, "gpt-4o-mini")
            history_tool = next(t for t in agent.tools if "symbol_history" in t.name.lower())

            result = await history_tool.on_invoke_tool(None, '{"agent_name": "Warren", "symbol": "AAPL", "days": 30}')

            assert isinstance(result, ToolError)
            assert "Unexpected error" in result.error
            assert "Request timed out" in result.error
            assert result.error_type == "unknown"
