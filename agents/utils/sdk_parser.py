"""SDK parsing utilities for OpenAI Agents SDK results.

Uses isinstance() with SDK classes (ToolCallItem, ToolCallOutputItem) as
recommended by official OpenAI documentation. Extracts tool calls from
agent results.
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Import SDK item types for isinstance() checks
from agents.items import RunItem, ToolCallItem, ToolCallOutputItem


# Tool name constants
TOOL_RESEARCHER = "Researcher"
TOOL_DECIDE_ACTION = "decide_action"

# Query extraction constants
DEFAULT_QUERY = "Market research"
MAX_LOOKBACK_ITEMS = 5
MAX_QUERY_LENGTH = 150


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


def extract_researcher_query(
    items: List[Any],
    current_index: int,
    default: str = DEFAULT_QUERY,
    max_lookback: int = MAX_LOOKBACK_ITEMS,
    max_length: int = MAX_QUERY_LENGTH,
) -> str:
    """Extract query from the most recent Researcher tool call.
    
    Looks backward from current_index through items to find the most
    recent Researcher tool call and extract its query argument.
    
    Args:
        items: List of SDK result items
        current_index: Index to search backward from
        default: Default query if not found
        max_lookback: Maximum items to search backward
        max_length: Maximum query length (truncated if longer)
    
    Returns:
        Query string from Researcher tool call, or default if not found
    """
    if current_index <= 0:
        return default
    
    # Calculate search range
    start = current_index - 1
    stop = max(0, current_index - max_lookback)
    
    for j in range(start, stop - 1, -1):
        item = items[j]
        
        # Check if item has tool_calls attribute
        tool_calls = getattr(item, "tool_calls", None)
        if not tool_calls:
            continue
        
        # Search tool calls for Researcher
        for tool_call in tool_calls:
            name = getattr(tool_call, "name", None)
            if name != TOOL_RESEARCHER:
                continue
            
            # Found Researcher - extract query from arguments
            arguments = getattr(tool_call, "arguments", None)
            if arguments is None:
                continue
            
            try:
                # Parse arguments (may be string or dict)
                args = json.loads(arguments) if isinstance(arguments, str) else arguments
                
                # Try common argument names
                query = args.get("query") or args.get("request") or args.get("message") or default
                
                # Truncate if needed
                if isinstance(query, str) and len(query) > max_length:
                    return query[:max_length]
                return query if isinstance(query, str) else default
                
            except (json.JSONDecodeError, TypeError, AttributeError):
                # Continue searching if this tool call fails to parse
                continue
    
    return default
