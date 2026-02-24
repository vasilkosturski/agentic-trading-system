"""Tests for SDK parser utilities."""

from unittest.mock import MagicMock, create_autospec

import pytest

from agents.items import ToolCallItem, ToolCallOutputItem
from utils.sdk_parser import (
    TOOL_RESEARCHER,
    TOOL_DECIDE_ACTION,
    ParsedToolCall,
    extract_tool_calls,
    get_tool_errors,
    _detect_tool_error,
    _SDK_ERROR_PREFIX,
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
        item.raw_item.arguments = "{}"

        # Create mock ToolCallOutputItem (call_id is on raw_item, not item)
        output_item = create_autospec(ToolCallOutputItem, instance=True)
        output_item.raw_item = {"call_id": "call_123", "output": "Research results"}
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
        item1.raw_item.arguments = "{}"

        output1 = create_autospec(ToolCallOutputItem, instance=True)
        output1.raw_item = {"call_id": "call_1"}
        output1.output = "Result 1"

        # Second tool
        item2 = create_autospec(ToolCallItem, instance=True)
        item2.raw_item = MagicMock()
        item2.raw_item.name = "decide_action"
        item2.raw_item.call_id = "call_2"
        item2.raw_item.arguments = "{}"

        output2 = create_autospec(ToolCallOutputItem, instance=True)
        output2.raw_item = {"call_id": "call_2"}
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


class TestErrorDetection:
    """Test SDK error detection — prefix matching."""

    def test_sdk_error_prefix_matches_installed_sdk(self):
        """Verify our prefix matches the SDK's default_tool_error_function.

        This test pins our detection against the installed SDK version.
        If an SDK upgrade changes the error prefix, this test fails
        immediately — preventing silent detection breakage.
        """
        from agents.tool import default_tool_error_function

        error = Exception("test error")
        output = default_tool_error_function(None, error)

        assert output.lower().startswith(_SDK_ERROR_PREFIX), (
            f"SDK error prefix mismatch! SDK produces: '{output[:80]}', "
            f"we match: '{_SDK_ERROR_PREFIX}'"
        )

    def test_detect_sdk_error_output(self):
        """Detect error from SDK's default error function output."""
        output = "An error occurred while running the tool. Please try again. Error: connection refused"
        is_error, message = _detect_tool_error(output)
        assert is_error is True
        assert message == output

    def test_detect_normal_output(self):
        """Normal tool output is not flagged as error."""
        output = '{"symbol": "AAPL", "price": 180.50}'
        is_error, message = _detect_tool_error(output)
        assert is_error is False
        assert message is None

    def test_detect_empty_output(self):
        """Empty output is not an error."""
        is_error, message = _detect_tool_error("")
        assert is_error is False
        assert message is None

    def test_error_message_truncated_at_500(self):
        """Error messages are truncated to 500 chars."""
        output = "An error occurred while running the tool. " + "x" * 600
        is_error, message = _detect_tool_error(output)
        assert is_error is True
        assert len(message) == 500

    def test_get_tool_errors_filters_correctly(self):
        """get_tool_errors returns only error tool calls."""
        calls = [
            ParsedToolCall(name="good_tool", call_id="1", output="ok", is_error=False),
            ParsedToolCall(name="bad_tool", call_id="2", output="err", is_error=True, error_message="fail"),
            ParsedToolCall(name="another_good", call_id="3", output="ok", is_error=False),
        ]
        errors = get_tool_errors(calls)
        assert len(errors) == 1
        assert errors[0].name == "bad_tool"
