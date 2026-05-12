"""Pydantic models for the new Trading Runs API.

These models match the Java DTOs in backend:
- CreateRunRequest
- UpdatePhaseRequest
- CompleteRunRequest

Uses camelCase field names to match Java naming convention directly.
"""

from enum import Enum
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

from models.usage_metrics import UsageMetrics


class RunPhase(str, Enum):
    """Run phase enum matching backend RunPhase.java"""
    INITIALIZING = "INITIALIZING"
    RESEARCHING = "RESEARCHING"
    DECIDING = "DECIDING"
    TRADING = "TRADING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


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
    title: str | None = None
    url: str | None = None
    description: str | None = None

    @classmethod
    def web(cls, title: str, url: str) -> "SourceDto":
        """Create a web source."""
        return cls(type="web", title=title, url=url)

    @classmethod
    def system_context(cls, description: str) -> "SourceDto":
        """Create a system context source."""
        return cls(type="system_context", description=description)


class ToolCallDto(BaseModel):
    """Unified tool call record for all phases (research, decision).

    Matches backend ToolCallDto.java.
    Fields:
    - tool: Tool name (e.g., "query_holdings", "brave_search")
    - params: Optional parameters (e.g., {"symbol": "JPM"})
    - error: Whether the tool call returned an error
    - errorMessage: Truncated error output (max 500 chars)
    """
    tool: str
    params: Dict[str, Any] | None = None
    error: bool | None = None
    errorMessage: str | None = None


class ReasoningDto(BaseModel):
    """Structured reasoning for decision phase.

    Matches backend ReasoningDto.java.
    4-field structured reasoning: rationale narrative, portfolio context,
    historical context, research summary.
    """
    rationale: str | None = None
    portfolioContext: str | None = None
    historicalContext: str | None = None
    researchContext: str | None = None


class ResearchPhaseData(BaseModel):
    """Research phase data for CompleteRunData.

    Matches backend ResearchPhaseDto.java.
    Contains all data collected during the RESEARCHING phase.
    """
    candidates: List[str] = Field(default_factory=list)
    sources: List[SourceDto] = Field(default_factory=list)
    notes: str | None = None
    toolCalls: List[ToolCallDto] = Field(default_factory=list)
    latencyMs: int | None = None
    # Token usage metrics (nested object)
    metrics: UsageMetrics | None = None
    # Agent prompts captured at execution time
    systemPrompt: str | None = None
    taskPrompt: str | None = None


class DecisionPhaseData(BaseModel):
    """Decision phase data for CompleteRunData.

    Matches backend DecisionPhaseDto.java.
    Contains all data collected during the DECIDING phase.
    """
    decision: TradeDecision
    symbol: str | None = None
    quantity: int | None = None
    reasoning: ReasoningDto | None = None
    sources: List[SourceDto] = Field(default_factory=list)
    toolCalls: List[ToolCallDto] = Field(default_factory=list)
    latencyMs: int | None = None
    # Token usage metrics (nested object)
    metrics: UsageMetrics | None = None
    # Agent prompts captured at execution time
    systemPrompt: str | None = None
    taskPrompt: str | None = None


class ExecutionPhaseData(BaseModel):
    """Execution phase data for CompleteRunData.

    Matches backend ExecutionPhaseDto.java.
    Contains all data collected during the TRADING phase.
    """
    tradeId: int | None = None
    status: PhaseStatus | None = None
    errorDetails: str | None = None


class CompleteRunData(BaseModel):
    """Request data for PUT /api/runs/{id}/complete.

    Matches backend CompleteRunRequest.java.
    Nested structure with explicit phase DTOs for self-documenting API.
    """
    research: ResearchPhaseData | None = None
    decision: DecisionPhaseData
    execution: ExecutionPhaseData | None = None

    def to_json_dict(self) -> Dict[str, Any]:
        """Serialize to dict for API."""
        return self.model_dump(exclude_none=True)
