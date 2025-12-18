"""Type-safe models for trading agents.

Follows Pydantic best practices:
- Pydantic BaseModel for external data (LLM output, API boundaries)
- dataclass for internal state
- type hints for simple primitives
"""

from .llm_output import TradingDecision, ResearchSource, HistoricalInsight
from .api_responses import PriceMetadata, HistoricalPrice, MarketIndicators, Holding
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
    # API Response Models
    "PriceMetadata",
    "HistoricalPrice",
    "MarketIndicators",
    "Holding",
    # Internal State Models
    "ExecutorState",
    "ToolCallRecord",
    "ResearchQueryRecord",
    "DataAccessRecord",
    "MarketConditions",
]
