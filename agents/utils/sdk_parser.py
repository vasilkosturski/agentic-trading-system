"""SDK parsing utilities for OpenAI Agents SDK results.

Uses isinstance() with SDK classes (ToolCallItem, ToolCallOutputItem) as
recommended by official OpenAI documentation. Extracts tool calls from
agent results.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

# Import SDK item types for isinstance() checks
from agents.items import RunItem, ToolCallItem, ToolCallOutputItem


# Tool name constants
TOOL_RESEARCHER = "Researcher"
TOOL_DECIDE_ACTION = "decide_action"


@dataclass
class ParsedToolCall:
    """Parsed tool call from SDK result item."""

    name: str
    call_id: str
    output: str


def extract_tool_calls(items: list[RunItem]) -> list[ParsedToolCall]:
    """Extract tool calls from SDK result items using isinstance().

    Uses SDK classes (ToolCallItem, ToolCallOutputItem) as recommended
    by OpenAI documentation. Maps call_id to tool names to associate
    outputs with their originating tool calls.

    Args:
        items: List of items from agent result.new_items

    Returns:
        List of ParsedToolCall with name, call_id, and output
    """
    tool_calls: List[ParsedToolCall] = []
    tool_name_by_call_id: Dict[str, str] = {}

    for item in items:
        # ToolCallItem: Record tool name mapping (no output yet)
        if isinstance(item, ToolCallItem):
            raw_item = item.raw_item
            if raw_item:
                name = getattr(raw_item, "name", None)
                call_id = getattr(raw_item, "call_id", None)
                if name and call_id:
                    tool_name_by_call_id[call_id] = name
            continue  # Wait for output item

        # ToolCallOutputItem: Has the actual output
        if isinstance(item, ToolCallOutputItem):
            call_id = getattr(item, "call_id", None)
            output = str(item.output) if item.output else ""

            # Look up tool name from earlier ToolCallItem
            if call_id and call_id in tool_name_by_call_id:
                tool_name = tool_name_by_call_id[call_id]
                tool_calls.append(
                    ParsedToolCall(name=tool_name, call_id=call_id, output=output)
                )

    return tool_calls
