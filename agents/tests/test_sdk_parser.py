"""Tests for SDK parser utilities."""

import json
from unittest.mock import MagicMock, create_autospec

import pytest

from agents.items import ToolCallItem, ToolCallOutputItem
from utils.sdk_parser import (
    TOOL_RESEARCHER,
    TOOL_DECIDE_ACTION,
    ParsedToolCall,
    extract_tool_calls,
    extract_researcher_query,
    DEFAULT_QUERY,
    MAX_LOOKBACK_ITEMS,
    MAX_QUERY_LENGTH,
)


class TestToolNameConstants:
    """Test tool name constants."""

    def test_researcher_constant(self):
        """Test Researcher tool constant."""
        assert TOOL_RESEARCHER == "Researcher"

    def test_decide_action_constant(self):
        """Test decide_action tool constant."""
        assert TOOL_DECIDE_ACTION == "decide_action"


class TestExtractToolCalls:
    """Test extract_tool_calls function using SDK classes."""

    def test_extract_from_tool_call_item(self):
        """Test extracting tool using isinstance() with SDK classes."""
        # Create mock ToolCallItem (spec makes isinstance work)
        item = create_autospec(ToolCallItem, instance=True)
        item.raw_item = MagicMock()
        item.raw_item.name = "Researcher"
        item.raw_item.call_id = "call_123"

        # Create mock ToolCallOutputItem
        output_item = create_autospec(ToolCallOutputItem, instance=True)
        output_item.call_id = "call_123"
        output_item.output = "Research results"

        calls = extract_tool_calls([item, output_item])

        assert len(calls) == 1
        assert calls[0].name == "Researcher"
        assert calls[0].call_id == "call_123"
        assert calls[0].output == "Research results"

    def test_extract_multiple_tools(self):
        """Test extracting multiple tool calls."""
        # First tool
        item1 = create_autospec(ToolCallItem, instance=True)
        item1.raw_item = MagicMock()
        item1.raw_item.name = "Researcher"
        item1.raw_item.call_id = "call_1"

        output1 = create_autospec(ToolCallOutputItem, instance=True)
        output1.call_id = "call_1"
        output1.output = "Result 1"

        # Second tool
        item2 = create_autospec(ToolCallItem, instance=True)
        item2.raw_item = MagicMock()
        item2.raw_item.name = "decide_action"
        item2.raw_item.call_id = "call_2"

        output2 = create_autospec(ToolCallOutputItem, instance=True)
        output2.call_id = "call_2"
        output2.output = "Result 2"

        calls = extract_tool_calls([item1, output1, item2, output2])

        assert len(calls) == 2
        assert calls[0].name == "Researcher"
        assert calls[1].name == "decide_action"

    def test_empty_items_list(self):
        """Test with empty items list."""
        calls = extract_tool_calls([])
        assert calls == []

    def test_items_without_tools(self):
        """Test items that don't match ToolCallItem or ToolCallOutputItem."""
        # Regular MagicMock won't match isinstance checks
        item = MagicMock()
        item.raw_item = None

        calls = extract_tool_calls([item])
        assert calls == []


class TestExtractResearcherQuery:
    """Test extract_researcher_query function."""

    def test_returns_default_when_index_zero(self):
        """Test returns default when current_index is 0."""
        result = extract_researcher_query([], 0)
        assert result == DEFAULT_QUERY

    def test_returns_default_when_index_negative(self):
        """Test returns default when current_index is negative."""
        result = extract_researcher_query([], -1)
        assert result == DEFAULT_QUERY

    def test_extracts_query_from_researcher_tool_call(self):
        """Test extracting query from Researcher tool call."""
        # Create item with tool_calls
        tool_call = MagicMock()
        tool_call.name = "Researcher"
        tool_call.arguments = json.dumps({"query": "Find AAPL news"})
        
        item = MagicMock()
        item.tool_calls = [tool_call]
        
        items = [item, MagicMock()]  # item at index 0, search from index 1
        
        result = extract_researcher_query(items, current_index=1)
        assert result == "Find AAPL news"

    def test_uses_request_fallback(self):
        """Test fallback to 'request' argument name."""
        tool_call = MagicMock()
        tool_call.name = "Researcher"
        tool_call.arguments = json.dumps({"request": "Stock analysis"})
        
        item = MagicMock()
        item.tool_calls = [tool_call]
        
        result = extract_researcher_query([item, MagicMock()], current_index=1)
        assert result == "Stock analysis"

    def test_uses_message_fallback(self):
        """Test fallback to 'message' argument name."""
        tool_call = MagicMock()
        tool_call.name = "Researcher"
        tool_call.arguments = json.dumps({"message": "Market update"})
        
        item = MagicMock()
        item.tool_calls = [tool_call]
        
        result = extract_researcher_query([item, MagicMock()], current_index=1)
        assert result == "Market update"

    def test_truncates_long_query(self):
        """Test truncation of long queries."""
        long_query = "x" * 200  # Longer than MAX_QUERY_LENGTH
        tool_call = MagicMock()
        tool_call.name = "Researcher"
        tool_call.arguments = json.dumps({"query": long_query})
        
        item = MagicMock()
        item.tool_calls = [tool_call]
        
        result = extract_researcher_query([item, MagicMock()], current_index=1)
        assert len(result) == MAX_QUERY_LENGTH
        assert result == "x" * MAX_QUERY_LENGTH

    def test_handles_dict_arguments(self):
        """Test handling arguments as dict (not string)."""
        tool_call = MagicMock()
        tool_call.name = "Researcher"
        tool_call.arguments = {"query": "Direct dict"}  # Dict, not JSON string
        
        item = MagicMock()
        item.tool_calls = [tool_call]
        
        result = extract_researcher_query([item, MagicMock()], current_index=1)
        assert result == "Direct dict"

    def test_skips_non_researcher_tools(self):
        """Test skipping non-Researcher tool calls."""
        other_tool = MagicMock()
        other_tool.name = "OtherTool"
        other_tool.arguments = json.dumps({"query": "Wrong tool"})
        
        researcher_tool = MagicMock()
        researcher_tool.name = "Researcher"
        researcher_tool.arguments = json.dumps({"query": "Right tool"})
        
        item1 = MagicMock()
        item1.tool_calls = [other_tool]
        
        item2 = MagicMock()
        item2.tool_calls = [researcher_tool]
        
        # Items: [item2 (researcher), item1 (other), current]
        items = [item2, item1, MagicMock()]
        
        result = extract_researcher_query(items, current_index=2)
        # Should skip item1 (OtherTool) and find item2 (Researcher)
        # Wait, we search backward from current_index-1 down to 0
        # index 2 -> search 1, 0
        # index 1 has OtherTool, index 0 has Researcher
        assert result == "Right tool"

    def test_respects_max_lookback(self):
        """Test that max_lookback limits search range."""
        # Put researcher at index 0, but set max_lookback to 2
        # Search from index 10, should only look at 9, 8 (not reach 0)
        tool_call = MagicMock()
        tool_call.name = "Researcher"
        tool_call.arguments = json.dumps({"query": "Too far back"})
        
        item_with_researcher = MagicMock()
        item_with_researcher.tool_calls = [tool_call]
        
        # Build items list: researcher at 0, empty items 1-9, current at 10
        items = [item_with_researcher] + [MagicMock() for _ in range(10)]
        for item in items[1:]:
            item.tool_calls = []
        
        result = extract_researcher_query(items, current_index=10, max_lookback=2)
        # Should not find it (too far back)
        assert result == DEFAULT_QUERY

    def test_handles_missing_tool_calls_attribute(self):
        """Test handling items without tool_calls attribute."""
        item = MagicMock(spec=[])  # No attributes
        
        result = extract_researcher_query([item, MagicMock()], current_index=1)
        assert result == DEFAULT_QUERY

    def test_handles_json_decode_error(self):
        """Test handling invalid JSON in arguments."""
        tool_call = MagicMock()
        tool_call.name = "Researcher"
        tool_call.arguments = "not valid json"
        
        item = MagicMock()
        item.tool_calls = [tool_call]
        
        result = extract_researcher_query([item, MagicMock()], current_index=1)
        # Should return default on parse error
        assert result == DEFAULT_QUERY
