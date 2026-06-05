from datetime import date as DateType
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DataTier(str, Enum):
    REAL = "REAL"
    MOCK = "MOCK"
    CACHED = "CACHED"


class TradeType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class RunOutcome(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    IN_PROGRESS = "IN_PROGRESS"


class PriceMetadata(BaseModel):
    price: float = Field(gt=0)
    cached: bool = Field(default=False)
    timestamp: datetime
    source: str


class HistoricalPrice(BaseModel):
    date: DateType
    price: float = Field(gt=0)


class MarketIndicators(BaseModel):
    sma5: float
    sma20: float
    volatility: float = Field(ge=0)


class MarketData(BaseModel):
    price: float = Field(gt=0)
    cached: bool = Field(default=False)
    timestamp: datetime
    source: str


class Holding(BaseModel):
    symbol: str = Field(min_length=1, max_length=5)
    quantity: int = Field(gt=0)
    averagePrice: float = Field(gt=0)


class AccountReport(BaseModel):
    agentName: str
    balance: float = Field(ge=0)
    holdingsValue: float = Field(ge=0)
    totalPortfolioValue: float = Field(ge=0)
    initialBalance: float = Field(gt=0)
    totalProfitLoss: float
    profitLossPercent: float
    lastUpdated: str | None = None
    holdingsCount: int = Field(ge=0)
    transactionCount: int = Field(ge=0)
    holdings: list[Holding] = Field(default_factory=list)


class AccountResponse(BaseModel):
    id: int
    name: str
    balance: float = Field(ge=0)


class ActivityTrade(BaseModel):
    type: TradeType
    symbol: str = Field(min_length=1, max_length=5)
    quantity: int = Field(gt=0)
    price: float = Field(gt=0)


class ActivityRun(BaseModel):
    date: datetime
    outcome: RunOutcome
    summary: str | None = None
    fullReasoning: str | None = None
    researchSources: str | None = None
    historicalContext: str | None = None
    trades: list[ActivityTrade] | None = None


class RecentActivityResponse(BaseModel):
    agentName: str
    days: int = Field(gt=0)
    runs: list[ActivityRun] = Field(default_factory=list)

    totalRuns: int = Field(default=0, ge=0)
    totalTrades: int = Field(default=0, ge=0)

    @property
    def computed_total_runs(self) -> int:
        return len(self.runs)

    @property
    def computed_total_trades(self) -> int:
        return sum(len(run.trades or []) for run in self.runs)


class SymbolPosition(BaseModel):
    shares: int = Field(ge=0)
    averageCost: float = Field(ge=0)


class SymbolTrade(BaseModel):
    date: str
    type: TradeType
    quantity: int = Field(gt=0)
    price: float = Field(gt=0)
    totalAmount: float


class TradingSummary(BaseModel):
    totalTrades: int = Field(ge=0)
    buys: int = Field(ge=0)
    sells: int = Field(ge=0)
    pattern: str = ""


class SymbolHistoryResponse(BaseModel):
    symbol: str = Field(min_length=1, max_length=5)
    agentName: str
    days: int = Field(gt=0)
    currentPosition: SymbolPosition | None = None
    trades: list[SymbolTrade] = Field(default_factory=list)
    summary: TradingSummary | None = None


class PriceLookupResponse(BaseModel):
    symbol: str = Field(min_length=1, max_length=5)
    price: float = Field(gt=0)
    timestamp: datetime


class TradeResult(BaseModel):
    tradeId: int = Field(gt=0)
    symbol: str = Field(min_length=1, max_length=5)
    quantity: int = Field(gt=0)
    price: float = Field(gt=0)
    newBalance: float = Field(ge=0)


class ToolError(BaseModel):
    error: str = Field(min_length=1)
    error_type: str = "unknown"
    context: dict = Field(default_factory=dict)
