from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Generic, Literal, TypeVar

from pydantic import BaseModel

from models.api_responses import RecentActivityResponse
from models.investment_style import InvestmentStyle
from models.llm_output import ResearchResponse, TradingDecision
from models.run_tracking import PhaseStatus, SourceDto
from models.usage_metrics import UsageMetrics

if TYPE_CHECKING:
    from models import Holding
    from models.run_tracking import ToolCallDto
    from utils.sdk_parser import ParsedToolCall


T = TypeVar("T")


@dataclass
class AgentRunResult(Generic[T]):
    output: T
    tool_calls: list["ParsedToolCall"] = field(default_factory=list)
    tool_errors: list["ParsedToolCall"] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.tool_errors) > 0

    @property
    def error_summary(self) -> str:
        if not self.tool_errors:
            return ""
        return "; ".join([f"{e.name}: {e.output[:100]}" for e in self.tool_errors])

    def raise_if_errors(self) -> None:
        if self.tool_errors:
            # Import here to avoid circular dependency
            from infra.exceptions import ToolExecutionError

            raise ToolExecutionError(
                f"Tools failed during execution: {[e.name for e in self.tool_errors]}",
                tool_errors=self.tool_errors,
            )


class SourceType(str, Enum):
    WEB = "web"
    SYSTEM_CONTEXT = "system_context"


class CycleResult(BaseModel):
    decision: TradingDecision | None = None
    trade_count: int
    run_id: int


@dataclass
class ResearchResult:
    research_response: ResearchResponse
    candidates: list[str] = field(default_factory=list)
    sources: list[SourceDto] = field(default_factory=list)
    notes: str = ""
    tool_calls: list["ToolCallDto"] = field(default_factory=list)
    usage_metrics: UsageMetrics | None = None
    research_latency_ms: int = 0
    guardrail_attempts: int = 1
    guardrail_issues: list[str] | None = None
    guardrail_outcome: Literal["first_try", "recovered", "exhausted"] = "first_try"
    guardrail_failed_output: dict | None = None


@dataclass
class DecisionResult:
    decision: TradingDecision
    decision_start_time: datetime
    tool_calls: list["ToolCallDto"] = field(default_factory=list)
    usage_metrics: UsageMetrics | None = None
    guardrail_attempts: int = 1
    guardrail_issues: list[str] | None = None
    guardrail_outcome: Literal["first_try", "recovered", "exhausted"] = "first_try"
    guardrail_failed_output: dict | None = None


@dataclass
class ExecutionResult:
    execution_status: PhaseStatus
    trade_id: int | None = None
    execution_error: str | None = None


@dataclass
class AccountData:
    balance: float
    holdings: list["Holding"]


@dataclass
class RunContext:
    run_id: int
    agent_id: int
    agent_name: str
    agent_style: InvestmentStyle
    model_name: str

    research_start_time: datetime
    balance: float = 0.0
    holdings: list["Holding"] = field(default_factory=list)
    recent_activity: RecentActivityResponse | None = None

    research: ResearchResult | None = None

    decision_result: DecisionResult | None = None
    decision_sources: list[SourceDto] = field(default_factory=list)

    market_analyst_system_prompt: str | None = None
    market_analyst_task_prompt: str | None = None
    decision_maker_system_prompt: str | None = None
    decision_maker_task_prompt: str | None = None

    execution_result: ExecutionResult | None = None


class HoldingsSummary(BaseModel):
    symbols: list[str]
    total_count: int

    def to_prompt_text(self) -> str:
        if not self.symbols:
            return "None"
        return ", ".join(self.symbols)

    @classmethod
    def from_holdings(cls, holdings: list) -> "HoldingsSummary":
        symbols = [h.symbol for h in holdings] if holdings else []
        return cls(symbols=symbols, total_count=len(symbols))
