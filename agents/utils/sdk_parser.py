"""SDK parsing utilities for OpenAI Agents SDK results.

Uses isinstance() with SDK classes (ToolCallItem, ToolCallOutputItem) as
recommended by official OpenAI documentation. Extracts tool calls from
agent results.

Uses proper typed access for SDK types:
- ResponseFunctionToolCall: Pydantic model with name, call_id, arguments
- FunctionCallOutput: TypedDict with call_id, output
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
                tool_calls.append(
                    ParsedToolCall(name=tool_name, call_id=call_id, output=output, params=params)
                )

    return tool_calls


def get_tool_errors(tool_calls: list[ParsedToolCall]) -> list[ParsedToolCall]:
    """Filter tool calls to return only those with errors.

    Detects errors by checking output for common error patterns:
    - Contains "error=" or "error_type="
    - Contains "Failed to" at start
    - Contains "Network error" or "Connection error"

    Args:
        tool_calls: List of ParsedToolCall from extract_tool_calls()

    Returns:
        List of ParsedToolCall that contain error outputs
    """
    error_patterns = [
        "error=",
        "error_type=",
        "Failed to ",
        "Network error",
        "Connection error",
        "api_error",
    ]

    errors = []
    for tc in tool_calls:
        output = tc.output.lower() if tc.output else ""
        if any(pattern.lower() in output for pattern in error_patterns):
            errors.append(tc)

    return errors
