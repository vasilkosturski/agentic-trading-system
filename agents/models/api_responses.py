"""Models for API response validation.

These use Pydantic BaseModel because they validate data from external APIs
(Java backend), which is an external boundary that needs validation.
"""

from datetime import datetime
from datetime import date as DateType
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# =============================================================================
# Enums for Type Safety
# =============================================================================

class DataTier(str, Enum):
    """Data quality tier from backend."""
    REAL = "REAL"
    MOCK = "MOCK"
    CACHED = "CACHED"


class TradeType(str, Enum):
    """Trade direction."""
    BUY = "BUY"
    SELL = "SELL"


class RunOutcome(str, Enum):
    """Outcome of a trading run."""
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


# =============================================================================
# Market Data Models
# =============================================================================

class PriceMetadata(BaseModel):
    """Stock price with data quality metadata (from backend API)."""

    price: float = Field(gt=0, description="Current stock price in USD")
    dataTier: DataTier = Field(description="Data quality tier: REAL, MOCK, or CACHED")
    timestamp: datetime = Field(description="Timestamp of price data")
    dataSource: str = Field(description="Data source name")
    dataAgeMinutes: int = Field(ge=0, description="Age of data in minutes")


class HistoricalPrice(BaseModel):
    """Single historical price point."""

    date: DateType = Field(description="Date of the price point")
    price: float = Field(gt=0, description="Closing price in USD")


class MarketIndicators(BaseModel):
    """Technical indicators for a stock."""

    sma5: float = Field(description="5-day simple moving average")
    sma20: float = Field(description="20-day simple moving average")
    volatility: float = Field(ge=0, description="Price volatility measure")


class Holding(BaseModel):
    """Stock holding from backend API.

    Validated at API boundary for type safety.
    """

    symbol: str = Field(min_length=1, max_length=5, description="Stock symbol")
    quantity: int = Field(gt=0, description="Number of shares held")
    averagePrice: float = Field(gt=0, description="Average purchase price per share")


# =============================================================================
# Memory API Response Models (for /api/memory/* endpoints)
# =============================================================================

class HoldingsResponse(BaseModel):
    """Response from /api/memory/holdings endpoint."""

    agentName: str = Field(description="Name of the trading agent")
    balance: float = Field(ge=0, description="Cash balance in USD")
    holdings: list[Holding] = Field(default_factory=list, description="List of stock holdings")
    positionCount: int = Field(ge=0, description="Number of positions held")


class ActivityTrade(BaseModel):
    """A trade within an activity run."""

    type: TradeType = Field(description="Trade type: BUY or SELL")
    symbol: str = Field(min_length=1, max_length=5, description="Stock symbol")
    quantity: int = Field(gt=0, description="Number of shares")
    price: float = Field(gt=0, description="Price per share")


class ActivityRun(BaseModel):
    """A single trading run in recent activity."""

    date: datetime = Field(description="Date/time of the run")
    outcome: RunOutcome = Field(description="Run outcome: COMPLETED or ERROR")
    summary: str = Field(default="", description="Brief summary of the run")
    fullReasoning: Optional[str] = Field(default=None, description="Complete reasoning")
    researchSources: Optional[str] = Field(default=None, description="JSON string of web sources")
    historicalContext: Optional[str] = Field(default=None, description="JSON string of historical insights")
    trades: list[ActivityTrade] = Field(default_factory=list, description="Trades made in this run")


class RecentActivityResponse(BaseModel):
    """Response from /api/memory/recent-activity endpoint.

    Note: totalRuns and totalTrades are computed from runs list.
    Backend may still send these fields for backwards compatibility,
    but they are ignored in favor of computed values.
    """

    agentName: str = Field(description="Name of the trading agent")
    days: int = Field(gt=0, description="Number of days of activity")
    runs: list[ActivityRun] = Field(default_factory=list, description="List of trading runs")

    # Keep fields for API compatibility but compute actual values
    totalRuns: int = Field(default=0, ge=0, description="Deprecated - use len(runs)")
    totalTrades: int = Field(default=0, ge=0, description="Deprecated - use computed_total_trades")

    @property
    def computed_total_runs(self) -> int:
        """Compute total runs from runs list (single source of truth)."""
        return len(self.runs)

    @property
    def computed_total_trades(self) -> int:
        """Compute total trades from runs list (single source of truth)."""
        return sum(len(run.trades) for run in self.runs)


class SymbolPosition(BaseModel):
    """Current position for a specific symbol."""

    shares: int = Field(ge=0, description="Number of shares held")
    averageCost: float = Field(ge=0, description="Average cost per share")


class SymbolTrade(BaseModel):
    """A trade for a specific symbol."""

    date: DateType = Field(description="Date of the trade")
    type: TradeType = Field(description="Trade type: BUY or SELL")
    quantity: int = Field(gt=0, description="Number of shares")
    price: float = Field(gt=0, description="Price per share")
    totalAmount: float = Field(description="Total trade amount")


class TradingSummary(BaseModel):
    """Summary of trading activity for a symbol."""

    totalTrades: int = Field(ge=0, description="Total number of trades")
    buys: int = Field(ge=0, description="Number of buy trades")
    sells: int = Field(ge=0, description="Number of sell trades")
    pattern: str = Field(default="", description="Detected trading pattern")


class SymbolHistoryResponse(BaseModel):
    """Response from /api/memory/trading-history endpoint."""

    symbol: str = Field(min_length=1, max_length=5, description="Stock symbol")
    agentName: str = Field(description="Name of the trading agent")
    days: int = Field(gt=0, description="Number of days of history")
    currentPosition: Optional[SymbolPosition] = Field(default=None, description="Current position if any")
    trades: list[SymbolTrade] = Field(default_factory=list, description="List of trades")
    summary: Optional[TradingSummary] = Field(default=None, description="Trading summary")


class PriceLookupResponse(BaseModel):
    """Response from price lookup (internal, not backend API)."""

    symbol: str = Field(min_length=1, max_length=5, description="Stock symbol")
    price: float = Field(gt=0, description="Current price in USD")
    timestamp: datetime = Field(description="Timestamp of lookup")


# =============================================================================
# Trade Execution Models
# =============================================================================

class TradeResult(BaseModel):
    """Result of a trade execution (buy/sell) from backend API.

    Matches Java TradeResult.java record.
    Contains essential data for trade confirmation and audit trail.
    """

    tradeId: int = Field(gt=0, description="Transaction ID for audit trail")
    symbol: str = Field(min_length=1, max_length=5, description="Stock symbol traded")
    quantity: int = Field(gt=0, description="Number of shares traded")
    price: float = Field(gt=0, description="Price per share at execution")
    newBalance: float = Field(ge=0, description="Updated cash balance after trade")


# =============================================================================
# Tool Error Model (for standardized error responses from LLM tools)
# =============================================================================

class ToolError(BaseModel):
    """Standardized error response for LLM tools.

    Used when a tool cannot return its normal response due to an error.
    The LLM receives this as a structured response it can interpret.
    """

    error: str = Field(min_length=1, description="Human-readable error message")
    error_type: str = Field(default="unknown", description="Error category: not_found, validation, api_error")
    context: dict = Field(default_factory=dict, description="Additional context (symbol, agent_name, etc.)")
