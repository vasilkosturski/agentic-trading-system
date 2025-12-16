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
