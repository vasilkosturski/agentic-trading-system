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
    ToolCallDto,
    ReasoningDto,
    CompleteRunData,
)
from .orchestration import (
    SourceType,
    CycleResult,
    RunContext,
    HoldingsSummary,
    AgentRunResult,
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
    "ToolCallDto",
    "ReasoningDto",
    "CompleteRunData",
    # Orchestration Models
    "SourceType",
    "CycleResult",
    "RunContext",
    "HoldingsSummary",
    # Agent Run Result (generic)
    "AgentRunResult",
]
