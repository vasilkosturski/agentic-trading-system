"""Models for internal agent state.

These use dataclass (not Pydantic) because they are internal data structures,
not external input that needs validation. Dataclass is faster and simpler
for internal-only data.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict
from datetime import datetime


@dataclass
class ExecutorState:
    """Internal state for AgentExecutor during a trading cycle."""

    run_id: Optional[int] = None
    trade_count: int = 0
    # Note: last_decision stored directly in AgentExecutor, not in this dataclass
    # This dataclass is for simple scalar state only


@dataclass
class ToolCallRecord:
    """Record of a tool call for transparency tracking."""

    tool: str
    inputs: Dict[str, Any]
    output: str  # Truncated to 500 chars
    timestamp: str


@dataclass
class ResearchQueryRecord:
    """Record of a research/search query."""

    query: str
    summary: str  # Truncated to 300 chars
    sources: List[Dict[str, str]]  # List of {title, url}
    timestamp: str


@dataclass
class DataAccessRecord:
    """Record of database or market data access."""

    type: str  # e.g., "Portfolio", "Trading History"
    details: str  # Truncated to 200 chars
    timestamp: str


@dataclass
class MarketConditions:
    """Market conditions captured at the start of a trading run."""

    timestamp: str  # ISO format timestamp
