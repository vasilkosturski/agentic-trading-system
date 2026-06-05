from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from models.usage_metrics import UsageMetrics


class RunPhase(str, Enum):
    INITIALIZING = "INITIALIZING"
    RESEARCHING = "RESEARCHING"
    DECIDING = "DECIDING"
    TRADING = "TRADING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PhaseStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class TradeDecision(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SourceDto(BaseModel):
    type: Literal["web", "system_context"]
    title: str | None = None
    url: str | None = None
    description: str | None = None

    @classmethod
    def web(cls, title: str, url: str) -> "SourceDto":
        return cls(type="web", title=title, url=url)

    @classmethod
    def system_context(cls, description: str) -> "SourceDto":
        return cls(type="system_context", description=description)


class ToolCallDto(BaseModel):
    tool: str
    params: dict[str, Any] | None = None
    error: bool | None = None
    errorMessage: str | None = None


class ReasoningDto(BaseModel):
    rationale: str | None = None
    portfolioContext: str | None = None
    historicalContext: str | None = None
    researchContext: str | None = None


class ResearchPhaseData(BaseModel):
    candidates: list[str] = Field(default_factory=list)
    sources: list[SourceDto] = Field(default_factory=list)
    notes: str | None = None
    toolCalls: list[ToolCallDto] = Field(default_factory=list)
    latencyMs: int | None = None
    metrics: UsageMetrics | None = None
    systemPrompt: str | None = None
    taskPrompt: str | None = None


class DecisionPhaseData(BaseModel):
    decision: TradeDecision
    symbol: str | None = None
    quantity: int | None = None
    reasoning: ReasoningDto | None = None
    sources: list[SourceDto] = Field(default_factory=list)
    toolCalls: list[ToolCallDto] = Field(default_factory=list)
    latencyMs: int | None = None
    metrics: UsageMetrics | None = None
    systemPrompt: str | None = None
    taskPrompt: str | None = None


class ExecutionPhaseData(BaseModel):
    tradeId: int | None = None
    status: PhaseStatus | None = None
    errorDetails: str | None = None


class CompleteRunData(BaseModel):
    research: ResearchPhaseData | None = None
    decision: DecisionPhaseData
    execution: ExecutionPhaseData | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)
