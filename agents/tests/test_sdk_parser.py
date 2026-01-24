"""Tests for SDK parser utilities."""

from unittest.mock import MagicMock, create_autospec

import pytest

from agents.items import ToolCallItem, ToolCallOutputItem
from utils.sdk_parser import (
    TOOL_RESEARCHER,
    TOOL_DECIDE_ACTION,
    ParsedToolCall,
    extract_tool_calls,
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
