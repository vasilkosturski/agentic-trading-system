"""Type-safe models for trading agents.

Follows Pydantic best practices:
- Pydantic BaseModel for external data (LLM output, API boundaries)
- dataclass for internal state
- type hints for simple primitives
"""

from .llm_output import TradingDecision, ResearchSource, HistoricalInsight, ResearchResponse
from .api_responses import (
    PriceMetadata,
    HistoricalPrice,
    MarketIndicators,
    Holding,
    # Memory API responses
    HoldingsResponse,
    ActivityTrade,
    ActivityRun,
    RecentActivityResponse,
    SymbolPosition,
    SymbolTrade,
    TradingSummary,
    SymbolHistoryResponse,
    PriceLookupResponse,
)
from .internal_state import (
    ExecutorState,
    ToolCallRecord,
    ResearchQueryRecord,
    DataAccessRecord,
    MarketConditions,
)

__all__ = [
    # LLM Output Models
    "TradingDecision",
    "ResearchSource",
    "HistoricalInsight",
    "ResearchResponse",
    # API Response Models - Market Data
    "PriceMetadata",
    "HistoricalPrice",
    "MarketIndicators",
    "Holding",
    # API Response Models - Memory API
    "HoldingsResponse",
    "ActivityTrade",
    "ActivityRun",
    "RecentActivityResponse",
    "SymbolPosition",
    "SymbolTrade",
    "TradingSummary",
    "SymbolHistoryResponse",
    "PriceLookupResponse",
    # Internal State Models
    "ExecutorState",
    "ToolCallRecord",
    "ResearchQueryRecord",
    "DataAccessRecord",
    "MarketConditions",
]
