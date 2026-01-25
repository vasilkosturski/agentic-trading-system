"""Orchestration models for AgentExecutor.

Typed models for internal data flow between phases, replacing Dict[str, Any].
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

from pydantic import BaseModel

from models.llm_output import TradingDecision, ResearchResponse

if TYPE_CHECKING:
    from models.run_tracking import SourceDto, ResearchToolCallDto, PhaseStatus
    from tool_tracking import ToolTracker


class SourceType(str, Enum):
    """Type of research source."""
    WEB = "web"
    SYSTEM_CONTEXT = "system_context"


class CycleResult(BaseModel):
    """Result of a complete trading cycle."""
    decision: Optional[TradingDecision] = None
    trade_count: int
    run_id: int


class SharedPhaseContext(BaseModel):
    """Data fetched once and shared across research and decision phases.
    
    Purpose:
    - Caching: Avoid duplicate API calls for same data
    - Consistency: Both agents see identical historical context
    """
    historical_context: str  # JSON: 30-day trading activity


@dataclass
class RunContext:
    """Context for a single trading run, passed through phases.
    
    Replaces instance variables in AgentExecutor for explicit data flow.
    All fields set at creation are guaranteed non-None.
    Optional fields are set as phases complete.
    
    Benefits:
    - Explicit data dependencies between phases
    - Testable in isolation (no hidden state)
    - No cleanup needed (context is discarded after cycle)
    """
    # Guaranteed at creation (Phase 1)
    run_id: int
    agent_id: int
    agent_name: str
    agent_style: str
    strategy: str
    model_name: str
    research_start_time: datetime
    
    # Tool tracker for local data collection
    tracker: Optional["ToolTracker"] = None
    
    # Set during execution
    decision_start_time: Optional[datetime] = None
    
    # Phase results (set as phases complete)
    shared_context: Optional[SharedPhaseContext] = None
    research_response: Optional[ResearchResponse] = None
    decision: Optional[TradingDecision] = None
    
    # Research phase data collection
    research_candidates: List[str] = field(default_factory=list)
    research_sources: List["SourceDto"] = field(default_factory=list)
    research_tool_calls: List["ResearchToolCallDto"] = field(default_factory=list)
    research_notes: str = ""
    
    # Execution phase data
    trade_id: Optional[int] = None
    trade_count: int = 0
    execution_status: Optional["PhaseStatus"] = None
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
