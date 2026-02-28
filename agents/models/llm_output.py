"""Models for LLM output validation.

These use Pydantic BaseModel because they validate data from LLMs,
which is untrusted external input that needs validation.
"""

from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class ResearchSource(BaseModel):
    """A web source cited in research (from Researcher tool)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, description="Article or page title")
    url: str = Field(min_length=1, pattern=r"^https?://", description="Full URL")


class HistoricalInsight(BaseModel):
    """An insight extracted from past trading history."""

    date: str = Field(description="Date of the insight (YYYY-MM-DD)")
    insight: str = Field(
        min_length=1, description="Specific insight with symbol, action, reasoning"
    )


class ResearchResponse(BaseModel):
    """Market Analyst agent's structured output.

    This is the response from the Market Analyst containing
    research findings, candidate stocks, and cited sources.
    """

    summary: str = Field(min_length=1, description="Research findings and analysis")
    candidates: list[str] = Field(
        default_factory=list,
        description="List of 3-5 stock symbols identified as potential candidates"
    )
    sources: list[ResearchSource] = Field(
        default_factory=list, description="List of cited web sources"
    )
    portfolio_context: str = Field(
        default="",
        description="How portfolio holdings and recent activity influenced research"
    )


class TradingDecision(BaseModel):
    """Agent's trading decision (validated LLM output).

    This is the core decision structure that comes from the LLM via decide_action tool.
    Must be validated strictly to prevent hallucinations or malformed decisions.
    """

    action: Literal["BUY", "SELL", "HOLD"] = Field(
        description="Trading action to take"
    )
    symbol: str = Field(
        default="", min_length=0, max_length=5, description="Stock symbol (empty for HOLD)"
    )
    quantity: int = Field(default=0, ge=0, description="Number of shares (0 for HOLD)")
    rationale: str = Field(description="Brief 1-2 sentence reason for decision")

    # Structured reasoning fields for ReasoningDto
    portfolioContext: str = Field(
        default="",
        description="Current portfolio state analysis: cash, positions, exposure"
    )
    historicalContext: str = Field(
        default="",
        description="Trading history context: past trades for this symbol/sector"
    )
    researchSummary: str = Field(
        default="",
        description="Summary of research findings: key points from sources"
    )
    candidateEvaluation: str = Field(
        default="",
        description="Candidate comparison: why this stock vs alternatives"
    )
    finalRationale: str = Field(
        default="",
        description="Final decision rationale: the complete reasoning"
    )

    # Legacy field - kept for backward compatibility
    fullReasoning: str = Field(
        default="", description="[DEPRECATED] Use structured fields instead"
    )
    researchSources: str = Field(
        default="[]",
        description="JSON string with research sources from Researcher tool",
    )

    model_config = ConfigDict(str_strip_whitespace=True)

    def validate_consistency(self) -> None:
        """Validate that action matches reasoning and required fields are present.

        Raises:
            ValueError: If decision is inconsistent
        """
        if self.action in ("BUY", "SELL"):
            if not self.symbol or self.quantity <= 0:
                raise ValueError(
                    f"symbol and positive quantity required for {self.action}"
                )

            # Check reasoning consistency
            reasoning_text = (self.rationale + " " + self.fullReasoning).lower()

            if self.action == "BUY" and ("sell" in reasoning_text or "selling" in reasoning_text):
                raise ValueError(
                    f"action=BUY but reasoning mentions 'sell'. Rationale: {self.rationale[:100]}"
                )

            if self.action == "SELL" and ("buy" in reasoning_text or "buying" in reasoning_text):
                raise ValueError(
                    f"action=SELL but reasoning mentions 'buy'. Rationale: {self.rationale[:100]}"
                )
