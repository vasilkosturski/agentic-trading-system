"""Shared UsageMetrics model for token usage tracking.

Used by both ResearchPhaseData and DecisionPhaseData to avoid
duplicating 8 flat metric fields. Serializes to camelCase to match
Java backend DTOs.
"""

from pydantic import BaseModel


class UsageMetrics(BaseModel):
    """Token usage metrics from OpenAI Agents SDK.

    Fields match the backend UsageMetricsDto (camelCase field names).
    """

    tokensUsed: int = 0
    inputTokens: int = 0
    outputTokens: int = 0
    numTurns: int = 0
    cachedTokens: int = 0
    reasoningTokens: int = 0
    modelName: str | None = None
    costUsd: float | None = None
