"""SDK parsing utilities for OpenAI Agents SDK results.

Uses isinstance() with SDK classes (ToolCallItem, ToolCallOutputItem) as
recommended by official OpenAI documentation. Extracts tool calls from
agent results.

Error detection: matches the SDK's default_tool_error_function prefix.
When a tool raises an exception, the SDK catches it and returns a string
starting with "An error occurred while running the tool". This is the
SDK's own deterministic output — not substring guessing.

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
            # call_id is on raw_item (FunctionCallOutput TypedDict or dict)
            raw_item = item.raw_item
            if isinstance(raw_item, dict):
                call_id = raw_item.get("call_id")
            else:
                call_id = getattr(raw_item, "call_id", None)
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
# Error Detection — SDK prefix match only
# ---------------------------------------------------------------------------

# SDK's default_tool_error_function produces this prefix when a tool raises.
# This is deterministic, not substring guessing — it's the SDK's own output.
_SDK_ERROR_PREFIX = "an error occurred while running the tool"


def _detect_tool_error(output: str) -> tuple[bool, Optional[str]]:
    """Detect tool errors by matching the SDK's default error prefix.

    When a tool raises an exception, the SDK's default_tool_error_function
    catches it and returns a string starting with a known prefix. We match
    that prefix. Nothing else.

    Returns:
        (is_error, error_message) tuple
    """
    lower = output.lower() if output else ""
    if lower.startswith(_SDK_ERROR_PREFIX):
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
