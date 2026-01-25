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
    # Trade execution
    TradeResult,
    # Tool error model
    ToolError,
)
from .internal_state import (
    ExecutorState,
    ToolCallRecord,
    ResearchQueryRecord,
    DataAccessRecord,
    MarketConditions,
)
from .run_tracking import (
    RunPhase,
    PhaseStatus,
    TradeDecision as RunTradeDecision,  # Avoid conflict with llm_output.TradingDecision
    SourceDto,
    ResearchToolCallDto,
    DecisionToolCallDto,
    ReasoningDto,
    CompleteRunData,
)
from .orchestration import (
    SourceType,
    CycleResult,
    SharedPhaseContext,
    RunContext,
    HoldingsSummary,
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
    # Trade Execution
    "TradeResult",
    # Tool Error Model
    "ToolError",
    # Internal State Models
    "ExecutorState",
    "ToolCallRecord",
    "ResearchQueryRecord",
    "DataAccessRecord",
    "MarketConditions",
    # Run Tracking Models (new Trading Runs API)
    "RunPhase",
    "PhaseStatus",
    "RunTradeDecision",
    "SourceDto",
    "ResearchToolCallDto",
    "DecisionToolCallDto",
    "ReasoningDto",
    "CompleteRunData",
    # Orchestration Models
    "SourceType",
    "CycleResult",
    "SharedPhaseContext",
    "RunContext",
    "HoldingsSummary",
]
