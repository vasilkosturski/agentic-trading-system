"""Tests for SDK parser utilities."""

from unittest.mock import MagicMock, create_autospec

from agents.items import ToolCallItem, ToolCallOutputItem

from utils.sdk_parser import (
    _SDK_ERROR_PREFIX,
    TOOL_DECIDE_ACTION,
    TOOL_RESEARCHER,
    ParsedToolCall,
    _detect_tool_error,
    extract_tool_calls,
    get_tool_errors,
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
        item = create_autospec(ToolCallItem, instance=True)
        item.raw_item = MagicMock()
        item.raw_item.name = "Researcher"
        item.raw_item.call_id = "call_123"
        item.raw_item.arguments = "{}"

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
        item1 = create_autospec(ToolCallItem, instance=True)
        item1.raw_item = MagicMock()
        item1.raw_item.name = "Researcher"
        item1.raw_item.call_id = "call_1"
        item1.raw_item.arguments = "{}"

        output1 = create_autospec(ToolCallOutputItem, instance=True)
        output1.raw_item = {"call_id": "call_1"}
        output1.output = "Result 1"

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


class TestErrorDetection:
    """Test SDK error detection — prefix matching and ToolError model detection."""

    def test_sdk_error_prefix_matches_installed_sdk(self):
        """Verify our prefix matches the SDK's default_tool_error_function."""
        from agents.tool import default_tool_error_function

        error = Exception("test error")
        output = default_tool_error_function(None, error)

        assert output.lower().startswith(_SDK_ERROR_PREFIX), (
            f"SDK error prefix mismatch! SDK produces: '{output[:80]}', "
            f"we match: '{_SDK_ERROR_PREFIX}'"
        )

    def test_detect_tool_error_model_api_error(self):
        """Detect ToolError model output with error_type='api_error'."""
        output = "error='HTTP 400: {\"message\": \"Bad request\"}' error_type='api_error' context={'agent_name': 'Warren', 'days': 30}"
        is_error, message = _detect_tool_error(output)
        assert is_error is True
        assert message == output

    def test_detect_normal_json_output(self):
        """Normal JSON tool output is not flagged as error."""
        output = '{"symbol": "AAPL", "price": 180.50}'
        is_error, message = _detect_tool_error(output)
        assert is_error is False
        assert message is None

    def test_get_tool_errors_filters_correctly(self):
        """get_tool_errors returns only error tool calls."""
        calls = [
            ParsedToolCall(name="good_tool", call_id="1", output="ok", is_error=False),
            ParsedToolCall(
                name="bad_tool", call_id="2", output="err", is_error=True, error_message="fail"
            ),
            ParsedToolCall(name="another_good", call_id="3", output="ok", is_error=False),
        ]
        errors = get_tool_errors(calls)
        assert len(errors) == 1
        assert errors[0].name == "bad_tool"
