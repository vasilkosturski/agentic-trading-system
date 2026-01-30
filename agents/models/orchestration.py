"""Orchestration models for AgentExecutor.

Typed models for internal data flow between operations, replacing Dict[str, Any].
Each operation has explicit input parameters and returns a typed result.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

from pydantic import BaseModel

from models.llm_output import TradingDecision, ResearchResponse
from models.run_tracking import SourceDto, PhaseStatus
from models.api_responses import RecentActivityResponse

if TYPE_CHECKING:
    from models.run_tracking import ResearchToolCallDto
    from tool_tracking import ToolTracker
    from models import Holding


class SourceType(str, Enum):
    """Type of research source."""
    WEB = "web"
    SYSTEM_CONTEXT = "system_context"


class CycleResult(BaseModel):
    """Result of a complete trading cycle."""
    decision: Optional[TradingDecision] = None
    trade_count: int
    run_id: int


# ============================================================================
# Operation Result Types - Each operation returns a typed result
# ============================================================================

@dataclass
class ResearchResult:
    """Result of market analyst research."""
    research_response: ResearchResponse  # Required - throw on failure
    candidates: List[str] = field(default_factory=list)
    sources: List[SourceDto] = field(default_factory=list)
    notes: str = ""


@dataclass
class DecisionResult:
    """Result of decision maker."""
    decision: TradingDecision  # Required - throw on failure
    decision_start_time: datetime  # Required - always set before returning


@dataclass
class ExecutionResult:
    """Result of trade execution."""
    execution_status: PhaseStatus  # Required - always set
    trade_id: Optional[int] = None  # None for HOLD actions
    execution_error: Optional[str] = None


@dataclass
class AccountData:
    """Account data fetched once at start of cycle.

    Replaces tuple[float, List[Holding]] return for named access.
    """
    balance: float
    holdings: List["Holding"]


@dataclass
class RunContext:
    """Context for a single trading run, passed through operations.

    Replaces instance variables in AgentExecutor for explicit data flow.
    All fields set at creation are guaranteed non-None.
    Optional fields are set as operations complete.

    Benefits:
    - Explicit data dependencies between operations
    - Testable in isolation (no hidden state)
    - No cleanup needed (context is discarded after cycle)
    """
    # Guaranteed at creation
    run_id: int
    agent_id: int
    agent_name: str
    agent_style: str
    model_name: str
    research_start_time: datetime

    # Tool tracker for local data collection
    tracker: Optional["ToolTracker"] = None

    # Account data (fetched once at start)
    balance: float = 0.0
    holdings: List["Holding"] = field(default_factory=list)

    # Recent trading activity (30-day history)
    recent_activity: Optional[RecentActivityResponse] = None

    # Set during execution
    decision_start_time: Optional[datetime] = None

    # Research results
    research_response: Optional[ResearchResponse] = None
    decision: Optional[TradingDecision] = None

    # Research phase data collection
    research_candidates: List[str] = field(default_factory=list)
    research_sources: List[SourceDto] = field(default_factory=list)
    research_tool_calls: List["ResearchToolCallDto"] = field(default_factory=list)
    research_notes: str = ""

    # Execution phase data
    trade_id: Optional[int] = None
    # trade_count removed - derive from trade_id: 1 if trade_id else 0
    execution_status: Optional[PhaseStatus] = None
    execution_error: Optional[str] = None


class HoldingsSummary(BaseModel):
    """Holdings data with built-in serialization for prompts."""
    symbols: List[str]
    total_count: int

    def to_prompt_text(self) -> str:
        """Serialize for LLM prompt consumption.

        Shows all holdings (no truncation for portfolios under max).
        """
        if not self.symbols:
            return "None"
        return ", ".join(self.symbols)

    @classmethod
    def from_holdings(cls, holdings: list) -> "HoldingsSummary":
        """Create from list of Holding objects."""
        symbols = [h.symbol for h in holdings] if holdings else []
        return cls(symbols=symbols, total_count=len(symbols))
