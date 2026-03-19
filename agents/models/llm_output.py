"""Models for LLM output validation.

These use Pydantic BaseModel because they validate data from LLMs,
which is untrusted external input that needs validation.
"""

from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class TradeAction(str, Enum):
    """Trading action enum for LLM-produced decisions.

    Uses (str, Enum) so Pydantic serializes values as plain strings,
    which is required for OpenAI structured-output compatibility.
    """
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class WebSource(BaseModel):
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


class CandidateStock(BaseModel):
    """A stock candidate with its verified price from lookup_price_tool.

    The Market Analyst populates this after calling lookup_price_tool
    for each candidate, ensuring prices are always available downstream.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    symbol: str = Field(
        min_length=1, max_length=5, description="Stock ticker symbol (e.g., AAPL)"
    )
    price: float = Field(gt=0, description="Current price from lookup_price_tool")


class ResearchResponse(BaseModel):
    """Market Analyst agent's structured output.

    This is the response from the Market Analyst containing
    research findings, candidate stocks, and cited sources.
    """

    summary: str = Field(min_length=1, description="Research findings and analysis")
    candidates: list[CandidateStock] = Field(
        default_factory=list,
        description="List of 3-5 stock candidates with their current prices"
    )
    webSources: list[WebSource] = Field(
        default_factory=list, description="List of cited web sources"
    )
    portfolio_context: str = Field(
        default="",
        description="How portfolio holdings and recent activity influenced research"
    )


class TradingDecision(BaseModel):
    """Agent's trading decision (validated LLM output).

    This is the core decision structure that comes from the LLM via structured output
    (output_type=TradingDecision). Must be validated strictly to prevent hallucinations
    or malformed decisions.
    """

    action: TradeAction = Field(description="Trading action to take")
    symbol: str = Field(
        default="", min_length=0, max_length=5, description="Stock symbol (empty for HOLD)"
    )
    quantity: int = Field(default=0, ge=0, description="Number of shares (0 for HOLD)")
    rationale: str = Field(description="Brief 1-2 sentence reason for decision")
    portfolioContext: str = Field(default="", description="Current portfolio state and how this trade fits")
    historicalContext: str = Field(default="", description="What trading history shows for this stock/sector")
    researchContext: str = Field(default="", description="Key findings from Market Analyst's research that drove this decision")

    model_config = ConfigDict(str_strip_whitespace=True)

    def validate_consistency(self) -> None:
        """Validate that action matches required fields.

        Raises:
            ValueError: If decision is structurally inconsistent
        """
        if self.action in (TradeAction.BUY, TradeAction.SELL):
            if not self.symbol or self.quantity <= 0:
                raise ValueError(
                    f"symbol and positive quantity required for {self.action}"
                )
