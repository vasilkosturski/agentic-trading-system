"""SDK parsing utilities for OpenAI Agents SDK results.

Uses isinstance() with SDK classes (ToolCallItem, ToolCallOutputItem) as
recommended by official OpenAI documentation. Extracts tool calls from
agent results.

Error detection covers two patterns:
1. SDK's default_tool_error_function prefix — when a tool raises, the SDK
   catches it and returns "An error occurred while running the tool …".
2. ToolError model returns — when a tool catches exceptions and returns a
   ``ToolError`` Pydantic model, the SDK serialises it as a string with
   distinctive ``error=`` and ``error_type=`` fields.

See: GitHub issue #2165 — SDK does not surface MCP isError for local tools.
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Import SDK item types for isinstance() checks
from agents.items import RunItem, ToolCallItem, ToolCallOutputItem

# Import OpenAI response types for proper typed access
from openai.types.responses.response_function_tool_call import ResponseFunctionToolCall


# Tool name constants
TOOL_RESEARCHER = "Researcher"
TOOL_DECIDE_ACTION = "decide_action"


@dataclass
class ParsedToolCall:
    """Parsed tool call from SDK result item."""

    name: str
    call_id: str
    output: str
    params: Optional[Dict[str, Any]] = None  # Tool input parameters
    is_error: bool = False
    error_message: Optional[str] = None


def extract_tool_calls(items: list[RunItem]) -> list[ParsedToolCall]:
    """Extract tool calls from SDK result items using isinstance().

    Uses SDK classes (ToolCallItem, ToolCallOutputItem) as recommended
    by OpenAI documentation. Maps call_id to tool names to associate
    outputs with their originating tool calls.

    Args:
        items: List of items from agent result.new_items

    Returns:
        List of ParsedToolCall with name, call_id, output, and params
    """
    tool_calls: List[ParsedToolCall] = []
    tool_name_by_call_id: Dict[str, str] = {}
    tool_params_by_call_id: Dict[str, Optional[Dict[str, Any]]] = {}

    for item in items:
        # ToolCallItem: Record tool name and params mapping (no output yet)
        if isinstance(item, ToolCallItem):
            raw_item = item.raw_item
            if not raw_item:
                continue

            # ResponseFunctionToolCall has guaranteed required fields
            if isinstance(raw_item, ResponseFunctionToolCall):
                tool_name_by_call_id[raw_item.call_id] = raw_item.name
                # Parse arguments (guaranteed str)
                try:
                    tool_params_by_call_id[raw_item.call_id] = json.loads(raw_item.arguments)
                except json.JSONDecodeError:
                    tool_params_by_call_id[raw_item.call_id] = {"raw": raw_item.arguments[:200]}
            else:
                # Dict or other tool types - need None checks
                if isinstance(raw_item, dict):
                    name = raw_item.get("name")
                    call_id = raw_item.get("call_id")
                    arguments = raw_item.get("arguments")
                else:
                    name = getattr(raw_item, "name", None)
                    call_id = getattr(raw_item, "call_id", None)
                    arguments = getattr(raw_item, "arguments", None)

                if name and call_id:
                    tool_name_by_call_id[call_id] = name
                    params = None
                    if arguments:
                        try:
                            params = json.loads(arguments) if isinstance(arguments, str) else arguments
                        except (json.JSONDecodeError, TypeError):
                            params = {"raw": str(arguments)[:200]}
                    tool_params_by_call_id[call_id] = params
            continue  # Wait for output item

        # ToolCallOutputItem: Has the actual output
        if isinstance(item, ToolCallOutputItem):
            # call_id is on output_raw_item (FunctionCallOutput TypedDict or dict)
            # SDK raw_item types differ between ToolCallItem and ToolCallOutputItem
            output_raw_item: Any = item.raw_item
            if isinstance(output_raw_item, dict):
                call_id = output_raw_item.get("call_id")
            else:
                call_id = getattr(output_raw_item, "call_id", None)
            output = str(item.output) if item.output else ""

            # Look up tool name and params from earlier ToolCallItem
            if call_id and call_id in tool_name_by_call_id:
                tool_name = tool_name_by_call_id[call_id]
                params = tool_params_by_call_id.get(call_id)
                is_error, error_message = _detect_tool_error(output)
                tool_calls.append(
                    ParsedToolCall(
                        name=tool_name,
                        call_id=call_id,
                        output=output,
                        params=params,
                        is_error=is_error,
                        error_message=error_message,
                    )
                )

    return tool_calls


# ---------------------------------------------------------------------------
# Error Detection — SDK prefix match + ToolError model detection
# ---------------------------------------------------------------------------

# SDK's default_tool_error_function produces this prefix when a tool raises.
# This is deterministic, not substring guessing — it's the SDK's own output.
_SDK_ERROR_PREFIX = "an error occurred while running the tool"


def _detect_tool_error(output: str) -> tuple[bool, Optional[str]]:
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
