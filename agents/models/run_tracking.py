"""Pydantic models for the new Trading Runs API.

These models match the Java DTOs in backend:
- CreateRunRequest
- UpdatePhaseRequest
- CompleteRunRequest

Uses camelCase field names to match Java naming convention directly.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class RunPhase(str, Enum):
    """Run phase enum matching backend RunPhase.java"""
    INITIALIZING = "INITIALIZING"
    RESEARCHING = "RESEARCHING"
    DECIDING = "DECIDING"
    TRADING = "TRADING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class PhaseStatus(str, Enum):
    """Execution phase status matching backend PhaseStatus.java"""
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class TradeDecision(str, Enum):
    """Trade decision enum matching backend TradeDecision.java"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SourceDto(BaseModel):
    """Source attribution for research and decision phases.

    Matches backend SourceDto.java.
    Two types:
    - web: Has title + url (verifiable)
    - system_context: Has description (internal tool usage)
    """
    type: Literal["web", "system_context"]
    title: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None

    @classmethod
    def web(cls, title: str, url: str) -> "SourceDto":
        """Create a web source."""
        return cls(type="web", title=title, url=url)

    @classmethod
    def system_context(cls, description: str) -> "SourceDto":
        """Create a system context source."""
        return cls(type="system_context", description=description)


class ResearchToolCallDto(BaseModel):
    """Tool call record for research phase.

    Matches backend ResearchToolCallDto.java.
    Simpler structure - no params, just tool name and duration.
    """
    tool: str
    durationMs: Optional[int] = None


class DecisionToolCallDto(BaseModel):
    """Tool call record for decision phase.

    Matches backend DecisionToolCallDto.java.
    Includes params for detailed tracking.
    """
    tool: str
    params: Optional[Dict[str, Any]] = None
    durationMs: Optional[int] = None


class ReasoningDto(BaseModel):
    """Structured reasoning for decision phase.

    Matches backend ReasoningDto.java.
    5-field structured reasoning as per system design.
    """
    portfolioContext: Optional[str] = None
    historicalContext: Optional[str] = None
    researchSummary: Optional[str] = None
    candidateEvaluation: Optional[str] = None
    finalRationale: Optional[str] = None


class ResearchPhaseData(BaseModel):
    """Research phase data for CompleteRunData.

    Matches backend ResearchPhaseDto.java.
    Contains all data collected during the RESEARCHING phase.
    """
    candidates: List[str] = Field(default_factory=list)
    sources: List[SourceDto] = Field(default_factory=list)
    notes: Optional[str] = None
    toolCalls: List[ResearchToolCallDto] = Field(default_factory=list)
    latencyMs: Optional[int] = None


class DecisionPhaseData(BaseModel):
    """Decision phase data for CompleteRunData.

    Matches backend DecisionPhaseDto.java.
    Contains all data collected during the DECIDING phase.
    """
    decision: TradeDecision
    symbol: Optional[str] = None
    quantity: Optional[int] = None
    reasoning: Optional[ReasoningDto] = None
    sources: List[SourceDto] = Field(default_factory=list)
    toolCalls: List[DecisionToolCallDto] = Field(default_factory=list)
    latencyMs: Optional[int] = None


class ExecutionPhaseData(BaseModel):
    """Execution phase data for CompleteRunData.

    Matches backend ExecutionPhaseDto.java.
    Contains all data collected during the TRADING phase.
    """
    tradeId: Optional[int] = None
    status: Optional[PhaseStatus] = None
    errorDetails: Optional[str] = None


class CompleteRunData(BaseModel):
    """Request data for PUT /api/runs/{id}/complete.

    Matches backend CompleteRunRequest.java.
    Nested structure with explicit phase DTOs for self-documenting API.
    """
    research: Optional[ResearchPhaseData] = None
    decision: DecisionPhaseData
    execution: Optional[ExecutionPhaseData] = None

    def to_json_dict(self) -> Dict[str, Any]:
        """Serialize to dict for API."""
        return self.model_dump(exclude_none=True)
