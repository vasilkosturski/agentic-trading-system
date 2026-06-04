"""SDK parsing utilities for OpenAI Agents SDK results.

Extracts tool calls from agent result items by pairing ToolCallItem (name +
params) with ToolCallOutputItem (output) via call_id.

Output strings come from raw_item["output"] which the SDK already serializes
(see ItemHelpers.tool_call_output_item → _convert_tool_output), so we never
need to guess the type of item.output ourselves.

Error detection covers two patterns:
1. SDK's default_tool_error_function prefix — "An error occurred …"
2. ToolError model returns — distinctive error= and error_type= fields.
"""

import json
from dataclasses import dataclass
from typing import Any

from agents.items import RunItem, ToolCallItem, ToolCallOutputItem

TOOL_RESEARCHER = "Researcher"
TOOL_DECIDE_ACTION = "decide_action"


@dataclass
class ParsedToolCall:
    """Parsed tool call from SDK result item."""

    name: str
    call_id: str
    output: str
    params: dict[str, Any] | None = None
    is_error: bool = False
    error_message: str | None = None


def _field(obj: Any, key: str) -> Any:
    """Read a field from a dict or object — handles both SDK raw_item shapes."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def extract_tool_calls(items: list[RunItem]) -> list[ParsedToolCall]:
    """Extract tool calls from SDK result items.

    Pairs ToolCallItem (name + params) with ToolCallOutputItem (output)
    via call_id. Output is read from raw_item which the SDK already
    serializes to a string.
    """
    tool_calls: list[ParsedToolCall] = []
    names: dict[str, str] = {}
    params: dict[str, dict[str, Any] | None] = {}

    for item in items:
        if isinstance(item, ToolCallItem):
            raw = item.raw_item
            if not raw:
                continue
            call_id = _field(raw, "call_id")
            name = _field(raw, "name")
            if not call_id or not name:
                continue
            names[call_id] = name
            args = _field(raw, "arguments")
            if args:
                try:
                    params[call_id] = json.loads(args) if isinstance(args, str) else args
                except (json.JSONDecodeError, TypeError):
                    params[call_id] = None

        elif isinstance(item, ToolCallOutputItem):
            raw = item.raw_item  # type: ignore[assignment]
            call_id = _field(raw, "call_id")
            # SDK serializes output via _convert_tool_output → str or list
            # (list when tool returns structured ToolOutputText/Image/File)
            raw_output = _field(raw, "output") or ""
            output = json.dumps(raw_output) if isinstance(raw_output, list) else str(raw_output)
            if call_id and call_id in names:
                is_error, error_msg = _detect_tool_error(output)
                tool_calls.append(
                    ParsedToolCall(
                        name=names[call_id],
                        call_id=call_id,
                        output=output,
                        params=params.get(call_id),
                        is_error=is_error,
                        error_message=error_msg,
                    )
                )

    return tool_calls


# ---------------------------------------------------------------------------
# Error Detection — SDK prefix match + ToolError model detection
# ---------------------------------------------------------------------------

# SDK's default_tool_error_function produces this prefix when a tool raises.
# This is deterministic, not substring guessing — it's the SDK's own output.
_SDK_ERROR_PREFIX = "an error occurred while running the tool"


def _detect_tool_error(output: str) -> tuple[bool, str | None]:
    """Detect tool errors from two sources.

    1. **SDK default prefix**: When a tool raises an exception, the SDK's
       default_tool_error_function catches it and returns a string starting
       with a known prefix.

    2. **ToolError model returns**: When a tool catches an exception and
       returns a ``ToolError`` Pydantic model, the SDK serialises it as a
       string like ``error='HTTP 400: ...' error_type='api_error' ...``.
       We detect the distinctive ``error_type=`` and ``error=`` fields.

    Returns:
        (is_error, error_message) tuple
    """
    if not output:
        return False, None

    lower = output.lower()

    # Pattern 1: SDK's default_tool_error_function prefix
    if lower.startswith(_SDK_ERROR_PREFIX):
        return True, output[:500]

    # Pattern 2: ToolError model string representation
    # Pydantic v2 str() produces: error='...' error_type='...' context={...}
    # Both fields must be present to avoid false positives on normal JSON/text.
    if "error_type=" in lower and "error=" in lower:
        return True, output[:500]

    return False, None


def get_tool_errors(tool_calls: list[ParsedToolCall]) -> list[ParsedToolCall]:
    """Filter tool calls to return only those with errors.

    Args:
        tool_calls: List of ParsedToolCall from extract_tool_calls()

    Returns:
        List of ParsedToolCall that contain error outputs
    """
    return [tc for tc in tool_calls if tc.is_error]
