"""Orchestration models for AgentExecutor.

Typed models for internal data flow between operations, replacing Dict[str, Any].
Each operation has explicit input parameters and returns a typed result.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Generic, TypeVar, TYPE_CHECKING

from pydantic import BaseModel

from models.investment_style import InvestmentStyle
from models.llm_output import TradingDecision, ResearchResponse
from models.run_tracking import SourceDto, PhaseStatus
from models.usage_metrics import UsageMetrics
from models.api_responses import RecentActivityResponse

if TYPE_CHECKING:
    from models.run_tracking import ToolCallDto
    from models import Holding
    from utils.sdk_parser import ParsedToolCall


# Generic type for agent output (ResearchResponse, TradingDecision, etc.)
T = TypeVar("T")


@dataclass
class AgentRunResult(Generic[T]):
    """Generic result from running an agent.

    Provides full visibility into what happened during agent execution:
    - output: The typed response (ResearchResponse, TradingDecision, etc.)
    - tool_calls: All tool calls made during execution
    - tool_errors: Any tools that returned error responses

    Usage:
        result = await market_analyst.run(context)

        # Option 1: Fail-fast (throw on errors)
        result.raise_if_errors()
        print(result.output.candidates)

        # Option 2: Handle errors gracefully
        if result.has_errors:
            log.warning(f"Partial failure: {result.error_summary}")
            # Continue with partial data or retry
        print(result.output.candidates)
    """
    output: T
    tool_calls: List["ParsedToolCall"] = field(default_factory=list)
    tool_errors: List["ParsedToolCall"] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if any tool calls returned errors."""
        return len(self.tool_errors) > 0

    @property
    def error_summary(self) -> str:
        """Get a summary of tool errors for logging."""
        if not self.tool_errors:
            return ""
        return "; ".join([f"{e.name}: {e.output[:100]}" for e in self.tool_errors])

    def raise_if_errors(self) -> None:
        """Raise ToolExecutionError if any tool calls failed.

        Opt-in fail-fast behavior. Call this when you want to stop
        processing if any tools returned errors.

        Raises:
            ToolExecutionError: If tool_errors is not empty
        """
        if self.tool_errors:
            # Import here to avoid circular dependency
            from exceptions import ToolExecutionError
            raise ToolExecutionError(
                f"Tools failed during execution: {[e.name for e in self.tool_errors]}",
                tool_errors=self.tool_errors
            )


class SourceType(str, Enum):
    """Type of research source."""
    WEB = "web"
    SYSTEM_CONTEXT = "system_context"


class CycleResult(BaseModel):
    """Result of a complete trading cycle."""
    decision: TradingDecision | None = None
    trade_count: int
    run_id: int


# ============================================================================
# Operation Result Types - Each operation returns a typed result
# ============================================================================

@dataclass
class ResearchResult:
    """Result of market analyst research.

    candidates is list[str] (symbol strings) for DB storage.
    Prices live inside research_response.candidates (CandidateStock objects).
    """
    research_response: ResearchResponse  # Required - throw on failure
    candidates: List[str] = field(default_factory=list)
    sources: List[SourceDto] = field(default_factory=list)
    notes: str = ""
    tool_calls: List["ToolCallDto"] = field(default_factory=list)
    usage_metrics: UsageMetrics | None = None
    # Wall-clock latency of the market analyst phase in milliseconds.
    # Set by _run_market_analyst so _finalize_run has a single source of
    # truth (the alternative — recomputing from decision_start_time minus
    # research_start_time — drifts by the time spent in _run_decision_maker
    # setup before decision_start_time was sampled).
    research_latency_ms: int = 0


@dataclass
class DecisionResult:
    """Result of decision maker."""
    decision: TradingDecision  # Required - throw on failure
    decision_start_time: datetime  # Required - always set before returning
    tool_calls: List["ToolCallDto"] = field(default_factory=list)
    usage_metrics: UsageMetrics | None = None


@dataclass
class ExecutionResult:
    """Result of trade execution."""
    execution_status: PhaseStatus  # Required - always set
    trade_id: int | None = None  # None for HOLD actions
    execution_error: str | None = None


@dataclass
class AccountData:
    """Account data fetched once at start of cycle.

    Replaces tuple[float, List[Holding]] return for named access.
    """
    balance: float
    holdings: List["Holding"]


@dataclass
class RunContext:
    """Context for a single trading run, passed through operations.

    Organized chronologically by phase (top to bottom = time flow):
    - PHASE 0: INITIALIZATION - Created at cycle start
    - PHASE 1: MARKET ANALYST (RESEARCHING) - Input → Output
    - PHASE 2: DECISION MAKER (DECIDING) - Input → Output
    - PHASE 3: EXECUTION (TRADING) - Input → Output

    Benefits:
    - Explicit data dependencies between operations
    - Testable in isolation (no hidden state)
    - No cleanup needed (context is discarded after cycle)
    """

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 0: INITIALIZATION (created at cycle start)
    # ═══════════════════════════════════════════════════════════════════════════
    run_id: int
    agent_id: int
    agent_name: str
    agent_style: InvestmentStyle
    model_name: str

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 1: MARKET ANALYST (RESEARCHING)
    # ═══════════════════════════════════════════════════════════════════════════
    # --- Input ---
    research_start_time: datetime
    balance: float = 0.0
    holdings: List["Holding"] = field(default_factory=list)
    recent_activity: RecentActivityResponse | None = None

    # --- Output (typed result, populated by _run_market_analyst) ---
    research: ResearchResult | None = None

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 2: DECISION MAKER (DECIDING)
    # ═══════════════════════════════════════════════════════════════════════════
    # --- Input: inherits research output above ---
    # --- Output (typed result, populated by _run_decision_maker) ---
    decision_result: DecisionResult | None = None
    # decision_sources is assembled in execute_cycle from cross-phase data
    # (research webSources + portfolio/activity system context), so it lives
    # here rather than inside DecisionResult.
    decision_sources: List[SourceDto] = field(default_factory=list)

    # ═══════════════════════════════════════════════════════════════════════════
    # PROMPT CAPTURE (for observability — populated during research/decision)
    # ═══════════════════════════════════════════════════════════════════════════
    market_analyst_system_prompt: str | None = None
    market_analyst_task_prompt: str | None = None
    decision_maker_system_prompt: str | None = None
    decision_maker_task_prompt: str | None = None

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 3: EXECUTION (TRADING)
    # ═══════════════════════════════════════════════════════════════════════════
    # --- Input: decision from above ---
    # --- Output (typed result, populated by execute_cycle) ---
    execution_result: ExecutionResult | None = None


class HoldingsSummary(BaseModel):
    """Holdings data with built-in serialization for prompts."""
    symbols: List[str]
    total_count: int

    def to_prompt_text(self) -> str:
        """Serialize for LLM prompt consumption.

        Shows all holdings (no truncation for portfolios under max).
        """
        if not self.symbols:
            return "None"
        return ", ".join(self.symbols)

    @classmethod
    def from_holdings(cls, holdings: list) -> "HoldingsSummary":
        """Create from list of Holding objects."""
        symbols = [h.symbol for h in holdings] if holdings else []
        return cls(symbols=symbols, total_count=len(symbols))
