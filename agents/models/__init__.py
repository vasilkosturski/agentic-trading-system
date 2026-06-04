"""Type-safe models for trading agents.

Follows Pydantic best practices:
- Pydantic BaseModel for external data (LLM output, API boundaries)
- dataclass for internal state
- type hints for simple primitives
"""

from .api_responses import (
    AccountReport,
    ActivityRun,
    # Memory API responses
    ActivityTrade,
    Holding,
    MarketData,
    PriceLookupResponse,
    PriceMetadata,
    RecentActivityResponse,
    SymbolHistoryResponse,
    SymbolPosition,
    SymbolTrade,
    # Tool error model
    ToolError,
    # Trade execution
    TradeResult,
    TradingSummary,
)
from .internal_state import (
    DataAccessRecord,
    ExecutorState,
    MarketConditions,
    ResearchQueryRecord,
    ToolCallRecord,
)
from .investment_style import InvestmentStyle
from .llm_output import CandidateStock, ResearchResponse, TradeAction, TradingDecision, WebSource
from .orchestration import (
    AgentRunResult,
    CycleResult,
    HoldingsSummary,
    RunContext,
    SourceType,
)
from .run_tracking import (
    CompleteRunData,
    PhaseStatus,
    ReasoningDto,
    RunPhase,
    SourceDto,
    ToolCallDto,
)
from .run_tracking import (
    TradeDecision as RunTradeDecision,  # Avoid conflict with llm_output.TradingDecision
)
from .usage_metrics import UsageMetrics

__all__ = [
    # Investment Style Enum
    "InvestmentStyle",
    # LLM Output Models
    "TradeAction",
    "TradingDecision",
    "WebSource",
    "CandidateStock",
    "ResearchResponse",
    # API Response Models - Market Data
    "MarketData",
    "Holding",
    "AccountReport",
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
    # Usage Metrics (shared across phases)
    "UsageMetrics",
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
