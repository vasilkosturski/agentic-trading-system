"""Models for API response validation.

These use Pydantic BaseModel because they validate data from external APIs
(Java backend), which is an external boundary that needs validation.
"""

from pydantic import BaseModel, Field


class PriceMetadata(BaseModel):
    """Stock price with data quality metadata (from backend API)."""

    price: float = Field(gt=0, description="Current stock price in USD")
    dataTier: str = Field(description="REAL, MOCK, or CACHED")
    timestamp: str = Field(description="ISO format timestamp")
    dataSource: str = Field(description="Data source name")
    dataAgeMinutes: int = Field(ge=0, description="Age of data in minutes")


class HistoricalPrice(BaseModel):
    """Single historical price point."""

    date: str = Field(description="Date in YYYY-MM-DD format")
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
