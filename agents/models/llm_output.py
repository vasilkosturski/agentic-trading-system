"""Models for LLM output validation.

These use Pydantic BaseModel because they validate data from LLMs,
which is untrusted external input that needs validation.
"""

from typing import Literal, Optional
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
    """Researcher agent's structured output.

    This is the response from the Researcher agent containing
    research findings and cited sources.
    """

    summary: str = Field(min_length=1, description="Research findings and analysis")
    sources: list[ResearchSource] = Field(
        default_factory=list, description="List of cited web sources"
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
    fullReasoning: str = Field(
        default="", description="Complete analysis and reasoning"
    )
    researchSources: str = Field(
        default="[]",
        description="JSON string with research sources from Researcher tool",
    )
    historicalContext: str = Field(
        default="[]",
        description="JSON string with insights from past trading history",
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
