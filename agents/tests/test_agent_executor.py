import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from agent_executor import AgentExecutor
from backend.run_lifecycle import RunLifecycle
from models.investment_style import InvestmentStyle
from models.llm_output import CandidateStock, ResearchResponse, TradingDecision, WebSource
from models.orchestration import (
    AccountData,
    CycleResult,
    ResearchResult,
    RunContext,
)
from phases.decision_phase import run_decision_phase
from phases.research_phase import run_research_phase


@pytest.fixture
def sample_agent_id():
    return 1


@pytest.fixture
def sample_agent_name():
    return "Warren"


@pytest.fixture
def sample_agent_style():
    return InvestmentStyle.VALUE


@pytest.fixture
def sample_strategy():
    return "Long-term value investing"


@pytest.fixture
def sample_model_name():
    return "gpt-4o-mini"


@pytest.fixture
def sample_balance():
    return 100000.0


@pytest.fixture
def sample_holdings():
    return []


@pytest.fixture
def sample_recent_activity():
    from models.api_responses import ActivityRun, ActivityTrade, RecentActivityResponse

    return RecentActivityResponse(
        agentName="Warren",
        days=30,
        runs=[
            ActivityRun(
                date="2025-12-10T10:00:00Z",
                outcome="COMPLETED",
                summary="Bought NVDA based on AI growth thesis",
                fullReasoning="AI growth thesis",
                researchSources=None,
                historicalContext=None,
                trades=[ActivityTrade(type="BUY", symbol="NVDA", quantity=50, price=145.0)],
            )
        ],
        totalRuns=1,
        totalTrades=1,
    )


@pytest.fixture
def sample_research_response():
    return ResearchResponse(
        candidates=[
            CandidateStock(symbol="AAPL", price=185.0),
            CandidateStock(symbol="NVDA", price=145.0),
        ],
        summary="Found 2 candidates",
        webSources=[
            WebSource(title="Article 1", url="https://example.com/1"),
            WebSource(title="Article 2", url="https://example.com/2"),
        ],
    )


@pytest.fixture
def sample_decision():
    return TradingDecision(
        action="BUY",
        symbol="AAPL",
        quantity=100,
        rationale="Strong growth",
        portfolioContext="Portfolio has room for more positions with available cash.",
        historicalContext="Previous AAPL trades have been profitable.",
        researchContext="Detailed analysis of AAPL fundamentals shows strong growth potential.",
    )


@pytest.fixture
def mock_mcp_pool():
    return MagicMock()


class TestAgentExecutorInitialization:
    def test_init(self, sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name):
        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name
        )

        assert executor.agent_id == sample_agent_id
        assert executor.name == sample_agent_name
        assert executor.agent_style == sample_agent_style
        assert executor.model_name == sample_model_name


@pytest.mark.asyncio
class TestAgentExecutorFetchData:
    @patch("agent_executor._get_account_report_raw")
    async def test_fetch_account_data_returns_account_data(
        self,
        mock_get_report,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_balance,
        sample_holdings,
    ):
        from models.api_responses import AccountReport

        mock_get_report.return_value = AccountReport(
            agentName=sample_agent_name,
            balance=sample_balance,
            holdingsValue=0.0,
            totalPortfolioValue=sample_balance,
            initialBalance=100000.0,
            totalProfitLoss=0.0,
            profitLossPercent=0.0,
            holdingsCount=len(sample_holdings),
            transactionCount=0,
            holdings=sample_holdings,
        )

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        result = await executor._fetch_account_data(sample_agent_id)

        assert isinstance(result, AccountData)
        assert result.balance == sample_balance
        assert result.holdings == sample_holdings

    @patch("agent_executor._get_account_report_raw")
    async def test_fetch_account_data_propagates_backend_api_error(
        self,
        mock_get_report,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
    ):
        from infra.exceptions import BackendAPIError

        mock_get_report.side_effect = BackendAPIError(
            "GET /api/agents/1/account-report failed", status_code=500
        )

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        with pytest.raises(BackendAPIError) as exc_info:
            await executor._fetch_account_data(sample_agent_id)

        assert exc_info.value.status_code == 500


@pytest.mark.asyncio
class TestAgentExecutorMarketAnalyst:
    @patch("phases.research_phase.MarketAnalyst")
    @patch("ai_agents.guardrail_retry.Runner")
    async def test_run_market_analyst_returns_research_result(
        self,
        mock_runner_class,
        mock_market_analyst_class,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        sample_research_response,
        sample_recent_activity,
        mock_mcp_pool,
    ):
        mock_analyst_instance = MagicMock()
        mock_analyst_instance.agent = MagicMock()
        mock_analyst_instance.build_prompt.return_value = "test prompt"
        mock_market_analyst_class.create = AsyncMock(return_value=mock_analyst_instance)

        mock_result = MagicMock()
        mock_result.final_output_as.return_value = sample_research_response
        mock_result.new_items = []
        mock_result.context_wrapper.usage.total_tokens = 100
        mock_result.context_wrapper.usage.input_tokens = 80
        mock_result.context_wrapper.usage.output_tokens = 20
        mock_result.context_wrapper.usage.input_tokens_details = None
        mock_result.context_wrapper.usage.output_tokens_details = None
        mock_result.context_wrapper.usage.requests = 1
        mock_result.context_wrapper.usage.request_usage_entries = []
        mock_runner_class.run = AsyncMock(return_value=mock_result)
        mock_analyst_instance.model_name = "gpt-4o"

        ctx = RunContext(
            run_id=123,
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name=sample_model_name,
            research_start_time=datetime.now(),
            balance=100000.0,
            holdings=[],
            recent_activity=sample_recent_activity,
        )

        result = await run_research_phase(ctx, mock_mcp_pool)

        assert isinstance(result, ResearchResult)
        assert result.research_response == sample_research_response
        assert len(result.candidates) == 2
        assert result.candidates == ["AAPL", "NVDA"]


@pytest.mark.asyncio
class TestAgentExecutorFullCycle:
    @patch("backend.run_lifecycle.complete_run")
    @patch("phases.execution_phase.buy_shares")
    @patch("phases.decision_phase.DecisionMaker")
    @patch("phases.research_phase.MarketAnalyst")
    @patch("phases.decision_phase.Runner")
    @patch("ai_agents.guardrail_retry.Runner")
    @patch("backend.run_lifecycle.update_phase")
    @patch("backend.run_lifecycle.create_run")
    @patch("agent_executor.get_backend_client")
    @patch("agent_executor._get_account_report_raw")
    @patch("backend.run_lifecycle.initialize_agent")
    @patch("backend.run_lifecycle.broadcast_status")
    async def test_execute_cycle_success_with_buy(
        self,
        mock_broadcast,
        mock_initialize,
        mock_get_report,
        mock_get_backend_client,
        mock_create_run,
        mock_update_phase,
        mock_guardrail_runner_class,
        mock_runner_class,
        mock_market_analyst_class,
        mock_decision_maker_class,
        mock_buy,
        mock_complete_run,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        sample_research_response,
        sample_recent_activity,
        sample_decision,
        mock_mcp_pool,
    ):
        # Setup mocks
        from models.api_responses import AccountReport

        mock_initialize.return_value = None
        mock_get_report.return_value = AccountReport(
            agentName=sample_agent_name,
            balance=100000.0,
            holdingsValue=0.0,
            totalPortfolioValue=100000.0,
            initialBalance=100000.0,
            totalProfitLoss=0.0,
            profitLossPercent=0.0,
            holdingsCount=0,
            transactionCount=0,
            holdings=[],
        )
        # Mock get_backend_client for _fetch_recent_activity
        mock_client = AsyncMock()
        mock_client.get_recent_activity.return_value = sample_recent_activity
        mock_get_backend_client.return_value = mock_client
        mock_create_run.return_value = 123
        mock_update_phase.return_value = True
        mock_complete_run.return_value = True

        # MarketAnalyst mock
        mock_analyst_instance = MagicMock()
        mock_analyst_instance.agent = MagicMock()
        mock_analyst_instance.agent.instructions = "test system prompt"
        mock_analyst_instance.build_prompt.return_value = "research prompt"
        mock_analyst_instance.model_name = "gpt-4o"
        mock_market_analyst_class.create = AsyncMock(return_value=mock_analyst_instance)

        # DecisionMaker mock
        mock_dm_instance = MagicMock()
        mock_dm_instance.agent = MagicMock()
        mock_dm_instance.agent.instructions = "test decision prompt"
        mock_dm_instance.build_prompt.return_value = "decision prompt"
        mock_dm_instance.model_name = "gpt-4o"
        mock_decision_maker_class.create = AsyncMock(return_value=mock_dm_instance)

        # Market Analyst runs through guardrail_retry.Runner
        mock_research_result = MagicMock()
        mock_research_result.final_output_as.return_value = sample_research_response
        mock_research_result.new_items = []
        mock_research_result.context_wrapper.usage.total_tokens = 100
        mock_research_result.context_wrapper.usage.input_tokens = 80
        mock_research_result.context_wrapper.usage.output_tokens = 20
        mock_research_result.context_wrapper.usage.input_tokens_details = None
        mock_research_result.context_wrapper.usage.output_tokens_details = None
        mock_research_result.context_wrapper.usage.requests = 1
        mock_research_result.context_wrapper.usage.request_usage_entries = []
        mock_guardrail_runner_class.run = AsyncMock(return_value=mock_research_result)
        mock_analyst_instance.model_name = "gpt-4o"

        # Decision Maker runs through phases.decision_phase.Runner
        mock_decision_result = MagicMock()
        mock_decision_result.final_output_as.return_value = sample_decision
        mock_decision_result.new_items = []
        mock_decision_result.context_wrapper.usage.total_tokens = 50
        mock_decision_result.context_wrapper.usage.input_tokens = 40
        mock_decision_result.context_wrapper.usage.output_tokens = 10
        mock_decision_result.context_wrapper.usage.input_tokens_details = None
        mock_decision_result.context_wrapper.usage.output_tokens_details = None
        mock_decision_result.context_wrapper.usage.requests = 1
        mock_decision_result.context_wrapper.usage.request_usage_entries = []
        mock_runner_class.run = AsyncMock(return_value=mock_decision_result)
        mock_dm_instance.model_name = "gpt-4o"

        # Trade execution
        mock_buy.return_value = MagicMock(tradeId=456)

        # Create executor and execute
        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name
        )

        result = await executor.execute_cycle(mcp_pool=mock_mcp_pool, force_trade=False)

        # Verify result
        assert isinstance(result, CycleResult)
        assert result.decision == sample_decision
        assert result.run_id == 123


@pytest.mark.asyncio
class TestAgentExecutorErrorPaths:
    @patch("backend.run_lifecycle.update_phase")
    @patch("backend.run_lifecycle.complete_run")
    @patch("backend.run_lifecycle.create_run")
    @patch("agent_executor.get_backend_client")
    @patch("agent_executor._get_account_report_raw")
    @patch("backend.run_lifecycle.initialize_agent")
    @patch("backend.run_lifecycle.broadcast_status")
    async def test_execute_cycle_propagates_recent_activity_backend_error(
        self,
        mock_broadcast,
        mock_initialize,
        mock_get_report,
        mock_get_backend_client,
        mock_create_run,
        mock_complete_run,
        mock_update_phase,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        mock_mcp_pool,
    ):
        from infra.exceptions import BackendAPIError
        from models.api_responses import AccountReport

        mock_initialize.return_value = None
        mock_get_report.return_value = AccountReport(
            agentName=sample_agent_name,
            balance=100000.0,
            holdingsValue=0.0,
            totalPortfolioValue=100000.0,
            initialBalance=100000.0,
            totalProfitLoss=0.0,
            profitLossPercent=0.0,
            holdingsCount=0,
            transactionCount=0,
            holdings=[],
        )

        # Backend client get_recent_activity blows up with an API error.
        mock_client = AsyncMock()
        mock_client.get_recent_activity.side_effect = BackendAPIError(
            "GET /api/runs/recent failed", status_code=502
        )
        mock_get_backend_client.return_value = mock_client

        mock_create_run.return_value = 999
        mock_update_phase.return_value = True
        mock_complete_run.return_value = True

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name
        )

        with pytest.raises(BackendAPIError) as exc_info:
            await executor.execute_cycle(mcp_pool=mock_mcp_pool, force_trade=False)

        assert exc_info.value.status_code == 502
        # _handle_cycle_error must broadcast PHASE_ERROR for the agent.
        # ctx is None at this point (failure happened before RunContext was
        # built), so run_id falls back to None and update_phase must still be
        # invoked at most for the earlier RESEARCHING transition — never for
        # FAILED because run_id was set when lifecycle.start() completed.
        error_broadcasts = [
            call for call in mock_broadcast.call_args_list if call.args[2] == "FAILED"
        ]
        assert error_broadcasts, "expected PHASE_ERROR broadcast on failure"
        # complete_run must NOT have been called — the orchestrator deliberately
        # avoids overriding a failed run back to COMPLETED.
        mock_complete_run.assert_not_called()

    @patch("backend.run_lifecycle.complete_run")
    @patch("phases.decision_phase.DecisionMaker")
    @patch("phases.research_phase.MarketAnalyst")
    @patch("ai_agents.guardrail_retry.Runner")
    @patch("backend.run_lifecycle.update_phase")
    @patch("backend.run_lifecycle.create_run")
    @patch("agent_executor.get_backend_client")
    @patch("agent_executor._get_account_report_raw")
    @patch("backend.run_lifecycle.initialize_agent")
    @patch("backend.run_lifecycle.broadcast_status")
    async def test_execute_cycle_propagates_max_turns_exceeded_from_research(
        self,
        mock_broadcast,
        mock_initialize,
        mock_get_report,
        mock_get_backend_client,
        mock_create_run,
        mock_update_phase,
        mock_guardrail_runner_class,
        mock_market_analyst_class,
        mock_decision_maker_class,
        mock_complete_run,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        sample_recent_activity,
        mock_mcp_pool,
    ):
        from agents.exceptions import MaxTurnsExceeded

        from models.api_responses import AccountReport

        mock_initialize.return_value = None
        mock_get_report.return_value = AccountReport(
            agentName=sample_agent_name,
            balance=100000.0,
            holdingsValue=0.0,
            totalPortfolioValue=100000.0,
            initialBalance=100000.0,
            totalProfitLoss=0.0,
            profitLossPercent=0.0,
            holdingsCount=0,
            transactionCount=0,
            holdings=[],
        )
        mock_client = AsyncMock()
        mock_client.get_recent_activity.return_value = sample_recent_activity
        mock_get_backend_client.return_value = mock_client
        mock_create_run.return_value = 555
        mock_update_phase.return_value = True
        mock_complete_run.return_value = True

        mock_analyst_instance = MagicMock()
        mock_analyst_instance.agent = MagicMock()
        mock_analyst_instance.agent.instructions = "sys"
        mock_analyst_instance.build_prompt.return_value = "prompt"
        mock_analyst_instance.model_name = "gpt-4o"
        mock_market_analyst_class.create = AsyncMock(return_value=mock_analyst_instance)

        mock_guardrail_runner_class.run = AsyncMock(
            side_effect=MaxTurnsExceeded("agent looped too long")
        )

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name
        )

        with pytest.raises(MaxTurnsExceeded):
            await executor.execute_cycle(mcp_pool=mock_mcp_pool, force_trade=False)

        failed_calls = [
            call
            for call in mock_update_phase.call_args_list
            if len(call.args) >= 2 and getattr(call.args[1], "name", None) == "FAILED"
        ]
        assert failed_calls, "expected update_phase(run_id, RunPhase.FAILED) on MaxTurnsExceeded"
        mock_complete_run.assert_not_called()
        mock_decision_maker_class.create.assert_not_called()

    async def test_handle_cycle_error_without_ctx_skips_update_phase(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
    ):
        mock_lifecycle = Mock(spec=RunLifecycle)
        mock_lifecycle.fail = AsyncMock()

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)
        err = RuntimeError("init failure")

        await executor._handle_cycle_error(err, ctx=None, lifecycle=mock_lifecycle)

        mock_lifecycle.fail.assert_called_once_with(None, err)

    async def test_handle_cycle_error_swallows_cleanup_error(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        sample_recent_activity,
    ):
        mock_lifecycle = Mock(spec=RunLifecycle)
        mock_lifecycle.fail = AsyncMock()

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name
        )

        ctx = RunContext(
            run_id=777,
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name=sample_model_name,
            research_start_time=datetime.now(),
            balance=100000.0,
            holdings=[],
            recent_activity=sample_recent_activity,
        )

        err = RuntimeError("cycle boom")

        await executor._handle_cycle_error(err, ctx=ctx, lifecycle=mock_lifecycle)

        mock_lifecycle.fail.assert_called_once_with(777, err)

    async def test_handle_cycle_error_swallows_lifecycle_fail_exception(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
    ):
        """If ``RunLifecycle.fail`` itself raises, the cycle's original
        exception still has to propagate — _handle_cycle_error must not
        let a cleanup failure leak out of this method."""
        mock_lifecycle = Mock(spec=RunLifecycle)
        mock_lifecycle.fail = AsyncMock(side_effect=RuntimeError("cleanup boom"))

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name
        )

        err = RuntimeError("cycle boom")

        # Should return None, NOT raise. The caller re-raises ``err``; this
        # method's contract is best-effort cleanup.
        result = await executor._handle_cycle_error(err, ctx=None, lifecycle=mock_lifecycle)

        assert result is None
        mock_lifecycle.fail.assert_called_once_with(None, err)


@pytest.mark.asyncio
class TestAgentExecutorCycleLoggerBehavior:
    @patch("backend.run_lifecycle.complete_run")
    @patch("phases.execution_phase.buy_shares")
    @patch("phases.decision_phase.DecisionMaker")
    @patch("phases.research_phase.MarketAnalyst")
    @patch("phases.decision_phase.Runner")
    @patch("ai_agents.guardrail_retry.Runner")
    @patch("backend.run_lifecycle.update_phase")
    @patch("backend.run_lifecycle.create_run")
    @patch("agent_executor.get_backend_client")
    @patch("agent_executor._get_account_report_raw")
    @patch("backend.run_lifecycle.initialize_agent")
    @patch("backend.run_lifecycle.broadcast_status")
    async def test_execute_cycle_emits_start_and_end_info_logs(
        self,
        mock_broadcast,
        mock_initialize,
        mock_get_report,
        mock_get_backend_client,
        mock_create_run,
        mock_update_phase,
        mock_guardrail_runner_class,
        mock_runner_class,
        mock_market_analyst_class,
        mock_decision_maker_class,
        mock_buy,
        mock_complete_run,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        sample_research_response,
        sample_recent_activity,
        sample_decision,
        mock_mcp_pool,
        caplog,
    ):
        import logging

        from models.api_responses import AccountReport

        mock_initialize.return_value = None
        mock_get_report.return_value = AccountReport(
            agentName=sample_agent_name,
            balance=100000.0,
            holdingsValue=0.0,
            totalPortfolioValue=100000.0,
            initialBalance=100000.0,
            totalProfitLoss=0.0,
            profitLossPercent=0.0,
            holdingsCount=0,
            transactionCount=0,
            holdings=[],
        )
        mock_client = AsyncMock()
        mock_client.get_recent_activity.return_value = sample_recent_activity
        mock_get_backend_client.return_value = mock_client
        mock_create_run.return_value = 123
        mock_update_phase.return_value = True
        mock_complete_run.return_value = True

        mock_analyst_instance = MagicMock()
        mock_analyst_instance.agent = MagicMock()
        mock_analyst_instance.agent.instructions = "test system prompt"
        mock_analyst_instance.build_prompt.return_value = "research prompt"
        mock_analyst_instance.model_name = "gpt-4o"
        mock_market_analyst_class.create = AsyncMock(return_value=mock_analyst_instance)

        mock_dm_instance = MagicMock()
        mock_dm_instance.agent = MagicMock()
        mock_dm_instance.agent.instructions = "test decision prompt"
        mock_dm_instance.build_prompt.return_value = "decision prompt"
        mock_dm_instance.model_name = "gpt-4o"
        mock_decision_maker_class.create = AsyncMock(return_value=mock_dm_instance)

        mock_research_result = MagicMock()
        mock_research_result.final_output_as.return_value = sample_research_response
        mock_research_result.new_items = []
        mock_research_result.context_wrapper.usage.total_tokens = 100
        mock_research_result.context_wrapper.usage.input_tokens = 80
        mock_research_result.context_wrapper.usage.output_tokens = 20
        mock_research_result.context_wrapper.usage.input_tokens_details = None
        mock_research_result.context_wrapper.usage.output_tokens_details = None
        mock_research_result.context_wrapper.usage.requests = 1
        mock_research_result.context_wrapper.usage.request_usage_entries = []
        mock_guardrail_runner_class.run = AsyncMock(return_value=mock_research_result)

        mock_decision_result = MagicMock()
        mock_decision_result.final_output_as.return_value = sample_decision
        mock_decision_result.new_items = []
        mock_decision_result.context_wrapper.usage.total_tokens = 50
        mock_decision_result.context_wrapper.usage.input_tokens = 40
        mock_decision_result.context_wrapper.usage.output_tokens = 10
        mock_decision_result.context_wrapper.usage.input_tokens_details = None
        mock_decision_result.context_wrapper.usage.output_tokens_details = None
        mock_decision_result.context_wrapper.usage.requests = 1
        mock_decision_result.context_wrapper.usage.request_usage_entries = []
        mock_runner_class.run = AsyncMock(return_value=mock_decision_result)

        mock_buy.return_value = MagicMock(tradeId=456)

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name
        )

        with caplog.at_level(logging.INFO, logger="agent_executor"):
            await executor.execute_cycle(mcp_pool=mock_mcp_pool, force_trade=False)

        # Filter to records emitted by the agent_executor module logger.
        ae_records = [r for r in caplog.records if r.name == "agent_executor"]

        start_records = [
            r
            for r in ae_records
            if r.levelno == logging.INFO
            and "🤖" in r.getMessage()
            and "starting portfolio review" in r.getMessage()
            and sample_agent_name in r.getMessage()
        ]
        end_records = [
            r
            for r in ae_records
            if r.levelno == logging.INFO
            and "✅" in r.getMessage()
            and "completed portfolio review" in r.getMessage()
            and sample_agent_name in r.getMessage()
        ]

        assert start_records, (
            "Expected an INFO log record on the agent_executor logger "
            "containing '🤖' and 'starting portfolio review' — cycle-start "
            "must be a first-class log record, not a raw print()."
        )
        assert end_records, (
            "Expected an INFO log record on the agent_executor logger "
            "containing '✅' and 'completed portfolio review' — cycle-end "
            "must be a first-class log record, not a raw print()."
        )


#
# These tests pin the contract that:
#   * `_extract_usage_metrics` no longer uses a hardcoded $0.15/$0.60 formula.
#   * A module-level `MODEL_PRICING` table drives cost calculation.
#   * Unknown models fall back to `cost_usd = None` with a WARNING log.
#   * The warning is deduplicated via `_UNKNOWN_MODELS_WARNED` so a noisy
#     unknown model name doesn't flood the log on every cycle.


class TestExtractUsageMetricsPricing:
    @pytest.fixture(autouse=True)
    def _reset_warned_set(self):
        import infra.pricing as pricing

        pricing._UNKNOWN_MODELS_WARNED.clear()
        yield
        pricing._UNKNOWN_MODELS_WARNED.clear()

    @staticmethod
    def _make_usage_mock(input_tokens: int, output_tokens: int, model_name: str | None):
        usage = MagicMock()
        usage.input_tokens = input_tokens
        usage.output_tokens = output_tokens
        usage.total_tokens = input_tokens + output_tokens
        usage.requests = 1
        usage.input_tokens_details = None
        usage.output_tokens_details = None
        if model_name is None:
            usage.request_usage_entries = []
        else:
            entry = MagicMock()
            entry.model_name = model_name
            usage.request_usage_entries = [entry]
        return usage

    def test_known_model_uses_table_for_exact_cost(self):
        from infra.telemetry import extract_usage_metrics

        usage = self._make_usage_mock(
            input_tokens=1_000_000,
            output_tokens=500_000,
            model_name="gpt-4o-mini",
        )

        metrics = extract_usage_metrics(usage, model_name="ignored-fallback")

        assert metrics.costUsd == 0.45
        assert metrics.modelName == "gpt-4o-mini"

    def test_gpt_5_mini_uses_current_table_rates(self):
        from infra.telemetry import extract_usage_metrics

        usage = self._make_usage_mock(
            input_tokens=1_000_000,
            output_tokens=500_000,
            model_name="gpt-5-mini",
        )

        metrics = extract_usage_metrics(usage, model_name="ignored-fallback")

        assert metrics.costUsd == 1.25
        assert metrics.modelName == "gpt-5-mini"

    def test_unknown_model_returns_none_and_logs_warning(self, caplog):
        import logging

        from infra.telemetry import extract_usage_metrics

        usage = self._make_usage_mock(
            input_tokens=100_000,
            output_tokens=50_000,
            model_name="some-future-unknown-model",
        )

        with caplog.at_level(logging.WARNING, logger="infra.telemetry"):
            metrics = extract_usage_metrics(usage, model_name="ignored-fallback")

        assert metrics.costUsd is None
        assert metrics.modelName == "some-future-unknown-model"

        warning_records = [
            r
            for r in caplog.records
            if r.name == "infra.telemetry"
            and r.levelno == logging.WARNING
            and "No pricing entry" in r.getMessage()
            and "some-future-unknown-model" in r.getMessage()
        ]
        assert warning_records, (
            "Expected a WARNING log on the telemetry logger containing "
            "'No pricing entry' and the unknown model name; got: "
            f"{[(r.name, r.levelname, r.getMessage()) for r in caplog.records]}"
        )

    def test_warning_is_deduped_across_repeated_unknown_model_calls(self, caplog):
        import logging

        from infra.telemetry import extract_usage_metrics

        usage1 = self._make_usage_mock(
            input_tokens=100, output_tokens=50, model_name="dedupe-test-model"
        )
        usage2 = self._make_usage_mock(
            input_tokens=200, output_tokens=75, model_name="dedupe-test-model"
        )

        with caplog.at_level(logging.WARNING, logger="infra.telemetry"):
            m1 = extract_usage_metrics(usage1, model_name="ignored")
            m2 = extract_usage_metrics(usage2, model_name="ignored")

        assert m1.costUsd is None
        assert m2.costUsd is None

        warning_records = [
            r
            for r in caplog.records
            if r.name == "infra.telemetry"
            and r.levelno == logging.WARNING
            and "No pricing entry" in r.getMessage()
            and "dedupe-test-model" in r.getMessage()
        ]
        assert len(warning_records) == 1, (
            f"Expected exactly 1 WARNING for 'dedupe-test-model' across two "
            f"calls (dedupe via _UNKNOWN_MODELS_WARNED); got "
            f"{len(warning_records)}: "
            f"{[r.getMessage() for r in warning_records]}"
        )


#
# These tests pin the contract that:
#   * `_load_model_pricing()` reads the vendored model_prices.json and returns
#     a dict[str, tuple[float, float]] keyed by model name with
#     (input_per_1m_usd, output_per_1m_usd) values.
#   * Entries missing the cost fields (e.g. LiteLLM's leading "sample_spec"
#     placeholder) are skipped instead of crashing on KeyError/None math.
#   * Per-token LiteLLM values are converted to per-1M-token values by
#     multiplying by 1_000_000 to match this module's pricing convention.


class TestLoadModelPricing:
    def test_load_model_pricing_returns_dict_with_known_openai_models(self):
        from infra.pricing import _load_model_pricing

        pricing = _load_model_pricing()

        assert isinstance(pricing, dict)
        assert "gpt-4o-mini" in pricing, (
            "Vendored model_prices.json must contain a 'gpt-4o-mini' entry — "
            "it is the test-suite's primary pricing fixture."
        )
        assert "gpt-5-mini" in pricing, (
            "Vendored model_prices.json must contain a 'gpt-5-mini' entry — "
            "it is the runtime default model (config.OPENAI_MODEL)."
        )
        for name in ("gpt-4o-mini", "gpt-5-mini"):
            value = pricing[name]
            assert isinstance(value, tuple), f"{name} value must be a tuple, got {type(value)}"
            assert len(value) == 2, f"{name} value must be a 2-tuple, got len {len(value)}"
            input_per_m, output_per_m = value
            assert isinstance(input_per_m, float), f"{name} input rate must be float"
            assert isinstance(output_per_m, float), f"{name} output rate must be float"
            assert input_per_m > 0, f"{name} input rate must be positive, got {input_per_m}"
            assert output_per_m > 0, f"{name} output rate must be positive, got {output_per_m}"

    def test_load_model_pricing_skips_entries_without_cost_fields(self, tmp_path):
        from infra.pricing import _load_model_pricing

        fake_json = {
            "sample_spec": {
                "max_tokens": 1024,
                "litellm_provider": "openai",
            },
            "missing-output-cost": {
                "input_cost_per_token": 0.0000002,
            },
            "model-with-extra-string-entry": "not-a-dict",
            "real-model": {
                "input_cost_per_token": 0.0000002,
                "output_cost_per_token": 0.0000008,
                "litellm_provider": "openai",
            },
        }
        fixture_path = tmp_path / "fake_prices.json"
        fixture_path.write_text(json.dumps(fake_json))

        pricing = _load_model_pricing(path=fixture_path)

        assert "sample_spec" not in pricing
        assert "missing-output-cost" not in pricing
        assert "model-with-extra-string-entry" not in pricing
        assert "real-model" in pricing
        input_per_m, output_per_m = pricing["real-model"]
        assert input_per_m == pytest.approx(0.2)
        assert output_per_m == pytest.approx(0.8)


@pytest.mark.asyncio
class TestAgentExecutorPromptCaptureNarrowing:
    @patch("phases.research_phase.MarketAnalyst")
    @patch("ai_agents.guardrail_retry.Runner")
    async def test_market_analyst_string_instructions_captured_on_ctx(
        self,
        mock_runner_class,
        mock_market_analyst_class,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        sample_research_response,
        sample_recent_activity,
        mock_mcp_pool,
    ):
        mock_analyst_instance = MagicMock()
        mock_analyst_instance.agent = MagicMock()
        mock_analyst_instance.agent.instructions = "you are a market analyst"
        mock_analyst_instance.build_prompt.return_value = "research prompt"
        mock_analyst_instance.model_name = "gpt-4o"
        mock_market_analyst_class.create = AsyncMock(return_value=mock_analyst_instance)

        mock_result = MagicMock()
        mock_result.final_output_as.return_value = sample_research_response
        mock_result.new_items = []
        mock_result.context_wrapper.usage.total_tokens = 100
        mock_result.context_wrapper.usage.input_tokens = 80
        mock_result.context_wrapper.usage.output_tokens = 20
        mock_result.context_wrapper.usage.input_tokens_details = None
        mock_result.context_wrapper.usage.output_tokens_details = None
        mock_result.context_wrapper.usage.requests = 1
        mock_result.context_wrapper.usage.request_usage_entries = []
        mock_runner_class.run = AsyncMock(return_value=mock_result)

        ctx = RunContext(
            run_id=123,
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name=sample_model_name,
            research_start_time=datetime.now(),
            balance=100000.0,
            holdings=[],
            recent_activity=sample_recent_activity,
        )

        await run_research_phase(ctx, mock_mcp_pool)

        assert ctx.market_analyst_system_prompt == "you are a market analyst"

    @patch("phases.research_phase.MarketAnalyst")
    @patch("ai_agents.guardrail_retry.Runner")
    async def test_market_analyst_callable_instructions_capture_is_none_with_debug_log(
        self,
        mock_runner_class,
        mock_market_analyst_class,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        sample_research_response,
        sample_recent_activity,
        mock_mcp_pool,
        caplog,
    ):
        import logging

        dynamic_prompt = lambda *a, **kw: "dynamically rendered prompt"  # noqa: E731

        mock_analyst_instance = MagicMock()
        mock_analyst_instance.agent = MagicMock()
        mock_analyst_instance.agent.instructions = dynamic_prompt
        mock_analyst_instance.build_prompt.return_value = "research prompt"
        mock_analyst_instance.model_name = "gpt-4o"
        mock_market_analyst_class.create = AsyncMock(return_value=mock_analyst_instance)

        mock_result = MagicMock()
        mock_result.final_output_as.return_value = sample_research_response
        mock_result.new_items = []
        mock_result.context_wrapper.usage.total_tokens = 100
        mock_result.context_wrapper.usage.input_tokens = 80
        mock_result.context_wrapper.usage.output_tokens = 20
        mock_result.context_wrapper.usage.input_tokens_details = None
        mock_result.context_wrapper.usage.output_tokens_details = None
        mock_result.context_wrapper.usage.requests = 1
        mock_result.context_wrapper.usage.request_usage_entries = []
        mock_runner_class.run = AsyncMock(return_value=mock_result)

        ctx = RunContext(
            run_id=123,
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name=sample_model_name,
            research_start_time=datetime.now(),
            balance=100000.0,
            holdings=[],
            recent_activity=sample_recent_activity,
        )

        with caplog.at_level(logging.DEBUG, logger="phases.research_phase"):
            await run_research_phase(ctx, mock_mcp_pool)

        assert ctx.market_analyst_system_prompt is None

        callable_debug_records = [
            r
            for r in caplog.records
            if r.name == "phases.research_phase"
            and r.levelno == logging.DEBUG
            and "ai_agents.market_analyst.agent.instructions is callable" in r.getMessage()
        ]
        assert callable_debug_records, (
            "Expected a DEBUG log on phases.research_phase announcing the "
            "callable branch was hit; got none. caplog records: "
            f"{[(r.name, r.levelname, r.getMessage()) for r in caplog.records]}"
        )

    @patch("phases.decision_phase.DecisionMaker")
    @patch("backend.run_lifecycle.update_phase")
    @patch("phases.decision_phase.Runner")
    async def test_decision_maker_callable_instructions_capture_is_none_with_debug_log(
        self,
        mock_runner_class,
        mock_update_phase,
        mock_decision_maker_class,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        sample_research_response,
        sample_decision,
        sample_recent_activity,
        mock_mcp_pool,
        caplog,
    ):
        import logging

        mock_update_phase.return_value = True

        dynamic_prompt = lambda *a, **kw: "dynamic decision prompt"  # noqa: E731

        mock_dm_instance = MagicMock()
        mock_dm_instance.agent = MagicMock()
        mock_dm_instance.agent.instructions = dynamic_prompt
        mock_dm_instance.build_prompt.return_value = "decision prompt"
        mock_dm_instance.model_name = "gpt-4o"
        mock_decision_maker_class.create = AsyncMock(return_value=mock_dm_instance)

        mock_result = MagicMock()
        mock_result.final_output_as.return_value = sample_decision
        mock_result.new_items = []
        mock_result.context_wrapper.usage.total_tokens = 50
        mock_result.context_wrapper.usage.input_tokens = 40
        mock_result.context_wrapper.usage.output_tokens = 10
        mock_result.context_wrapper.usage.input_tokens_details = None
        mock_result.context_wrapper.usage.output_tokens_details = None
        mock_result.context_wrapper.usage.requests = 1
        mock_result.context_wrapper.usage.request_usage_entries = []
        mock_runner_class.run = AsyncMock(return_value=mock_result)

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name
        )

        ctx = RunContext(
            run_id=123,
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name=sample_model_name,
            research_start_time=datetime.now(),
            balance=100000.0,
            holdings=[],
            recent_activity=sample_recent_activity,
            research=ResearchResult(research_response=sample_research_response),
        )

        mock_lifecycle = MagicMock(spec=RunLifecycle)

        # No AgentExecutor instance needed — run_decision_phase is a
        # module-level function (Task 7 of the decomposition).
        _ = executor  # silence unused-var without changing fixture wiring

        with caplog.at_level(logging.DEBUG, logger="phases.decision_phase"):
            await run_decision_phase(
                ctx=ctx,
                mcp_pool=mock_mcp_pool,
                force_trade=False,
                lifecycle=mock_lifecycle,
            )

        assert ctx.decision_maker_system_prompt is None

        callable_debug_records = [
            r
            for r in caplog.records
            if r.name == "phases.decision_phase"
            and r.levelno == logging.DEBUG
            and "ai_agents.decision_maker.agent.instructions is callable" in r.getMessage()
        ]
        assert callable_debug_records, (
            "Expected a DEBUG log on phases.decision_phase announcing the callable "
            "branch was hit at the Decision Maker site; got none. caplog records: "
            f"{[(r.name, r.levelname, r.getMessage()) for r in caplog.records]}"
        )


class TestAgentExecutorExtractRunTelemetry:
    @pytest.fixture(autouse=True)
    def _reset_warned_set(self):
        import infra.pricing as pricing

        pricing._UNKNOWN_MODELS_WARNED.clear()
        yield
        pricing._UNKNOWN_MODELS_WARNED.clear()

    @staticmethod
    def _make_run_result_mock(num_tool_calls: int):
        result = MagicMock()
        result.new_items = [MagicMock() for _ in range(num_tool_calls)]
        result.context_wrapper.usage.total_tokens = 300
        result.context_wrapper.usage.input_tokens = 100
        result.context_wrapper.usage.output_tokens = 200
        result.context_wrapper.usage.requests = 1
        result.context_wrapper.usage.input_tokens_details = None
        result.context_wrapper.usage.output_tokens_details = None
        result.context_wrapper.usage.request_usage_entries = []
        return result

    @staticmethod
    def _make_parsed_call(
        name: str, params: dict, is_error: bool = False, error_message: str | None = None
    ):
        pc = MagicMock()
        pc.name = name
        pc.params = params
        pc.is_error = is_error
        pc.error_message = error_message
        return pc

    def test_extract_run_telemetry_returns_tuple_with_tool_calls_and_metrics(
        self,
        caplog,
    ):
        import logging

        from infra.telemetry import extract_run_telemetry
        from models.run_tracking import ToolCallDto
        from models.usage_metrics import UsageMetrics

        mock_result = self._make_run_result_mock(num_tool_calls=2)

        parsed_calls = [
            self._make_parsed_call("fetch_quote", {"symbol": "AAPL"}),
            self._make_parsed_call("broken_tool", {"x": 1}, is_error=True, error_message="boom"),
        ]

        with patch("infra.telemetry.extract_tool_calls", return_value=parsed_calls) as mock_extract:
            with caplog.at_level(logging.INFO, logger="infra.telemetry"):
                tool_calls, usage_metrics = extract_run_telemetry(
                    mock_result,
                    model_name="gpt-4o-mini",
                    agent_label="Test Agent",
                )

        mock_extract.assert_called_once_with(mock_result.new_items)

        assert isinstance(tool_calls, list)
        assert all(isinstance(tc, ToolCallDto) for tc in tool_calls)
        assert len(tool_calls) == 2
        assert tool_calls[0].tool == "fetch_quote"
        assert tool_calls[0].params == {"symbol": "AAPL"}
        assert tool_calls[0].error is None  # is_error=False → error=None
        assert tool_calls[0].errorMessage is None
        assert tool_calls[1].tool == "broken_tool"
        assert tool_calls[1].error is True
        assert tool_calls[1].errorMessage == "boom"

        # Usage metrics shape + computed cost.
        assert isinstance(usage_metrics, UsageMetrics)
        assert usage_metrics.tokensUsed == 300
        assert usage_metrics.inputTokens == 100
        assert usage_metrics.outputTokens == 200
        assert usage_metrics.modelName == "gpt-4o-mini"
        # gpt-4o-mini: (0.15, 0.60) per 1M tokens
        # 100 * 0.15 / 1_000_000 + 200 * 0.60 / 1_000_000
        #   = 0.000015 + 0.00012
        #   = 0.000135
        assert usage_metrics.costUsd == 0.000135

        # Two observability log lines must be emitted with the agent label.
        ae_info = [
            r for r in caplog.records if r.name == "infra.telemetry" and r.levelno == logging.INFO
        ]
        made_records = [
            r
            for r in ae_info
            if "Test Agent made" in r.getMessage() and "2 tool calls" in r.getMessage()
        ]
        usage_records = [
            r
            for r in ae_info
            if "Test Agent usage" in r.getMessage()
            and "300 tokens" in r.getMessage()
            and "model=gpt-4o-mini" in r.getMessage()
        ]
        assert made_records, (
            "Expected an INFO log on telemetry with 'Test Agent made N tool "
            "calls'; got: "
            f"{[(r.name, r.levelname, r.getMessage()) for r in caplog.records]}"
        )
        assert usage_records, (
            "Expected an INFO log on telemetry with 'Test Agent usage: …'; "
            "got: "
            f"{[(r.name, r.levelname, r.getMessage()) for r in caplog.records]}"
        )


#
# Before this fix, the PHASE_COMPLETED broadcast outcome message branched on
# `ctx.trade_id` truthiness. A FAILED BUY/SELL leaves trade_id=None, so it was
# incorrectly labeled "No trades (HOLD decision)" — the same message as a
# legitimate HOLD. After the restructure the message branches on
# `ctx.execution_result.execution_status` with three explicit cases
# (COMPLETED / SKIPPED / FAILED) plus a defensive fallback.


@pytest.mark.asyncio
class TestAgentExecutorCompletionMessageOnFailure:
    @patch("backend.run_lifecycle.complete_run")
    @patch("phases.execution_phase.buy_shares")
    @patch("phases.decision_phase.DecisionMaker")
    @patch("phases.research_phase.MarketAnalyst")
    @patch("phases.decision_phase.Runner")
    @patch("ai_agents.guardrail_retry.Runner")
    @patch("backend.run_lifecycle.update_phase")
    @patch("backend.run_lifecycle.create_run")
    @patch("agent_executor.get_backend_client")
    @patch("agent_executor._get_account_report_raw")
    @patch("backend.run_lifecycle.initialize_agent")
    @patch("backend.run_lifecycle.broadcast_status")
    async def test_failed_buy_emits_trade_attempted_but_failed_message(
        self,
        mock_broadcast,
        mock_initialize,
        mock_get_report,
        mock_get_backend_client,
        mock_create_run,
        mock_update_phase,
        mock_guardrail_runner_class,
        mock_runner_class,
        mock_market_analyst_class,
        mock_decision_maker_class,
        mock_buy,
        mock_complete_run,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        sample_research_response,
        sample_recent_activity,
        sample_decision,
        mock_mcp_pool,
    ):
        from backend.status_broadcaster import PHASE_COMPLETED
        from models.api_responses import AccountReport

        mock_initialize.return_value = None
        mock_get_report.return_value = AccountReport(
            agentName=sample_agent_name,
            balance=100000.0,
            holdingsValue=0.0,
            totalPortfolioValue=100000.0,
            initialBalance=100000.0,
            totalProfitLoss=0.0,
            profitLossPercent=0.0,
            holdingsCount=0,
            transactionCount=0,
            holdings=[],
        )
        mock_client = AsyncMock()
        mock_client.get_recent_activity.return_value = sample_recent_activity
        mock_get_backend_client.return_value = mock_client
        mock_create_run.return_value = 123
        mock_update_phase.return_value = True
        mock_complete_run.return_value = True

        # MarketAnalyst mock
        mock_analyst_instance = MagicMock()
        mock_analyst_instance.agent = MagicMock()
        mock_analyst_instance.agent.instructions = "test system prompt"
        mock_analyst_instance.build_prompt.return_value = "research prompt"
        mock_analyst_instance.model_name = "gpt-4o"
        mock_market_analyst_class.create = AsyncMock(return_value=mock_analyst_instance)

        # DecisionMaker mock
        mock_dm_instance = MagicMock()
        mock_dm_instance.agent = MagicMock()
        mock_dm_instance.agent.instructions = "test decision prompt"
        mock_dm_instance.build_prompt.return_value = "decision prompt"
        mock_dm_instance.model_name = "gpt-4o"
        mock_decision_maker_class.create = AsyncMock(return_value=mock_dm_instance)

        # Market Analyst runs through guardrail_retry.Runner
        mock_research_result = MagicMock()
        mock_research_result.final_output_as.return_value = sample_research_response
        mock_research_result.new_items = []
        mock_research_result.context_wrapper.usage.total_tokens = 100
        mock_research_result.context_wrapper.usage.input_tokens = 80
        mock_research_result.context_wrapper.usage.output_tokens = 20
        mock_research_result.context_wrapper.usage.input_tokens_details = None
        mock_research_result.context_wrapper.usage.output_tokens_details = None
        mock_research_result.context_wrapper.usage.requests = 1
        mock_research_result.context_wrapper.usage.request_usage_entries = []
        mock_guardrail_runner_class.run = AsyncMock(return_value=mock_research_result)

        # Decision Maker runs through phases.decision_phase.Runner → BUY decision
        mock_decision_result = MagicMock()
        mock_decision_result.final_output_as.return_value = sample_decision
        mock_decision_result.new_items = []
        mock_decision_result.context_wrapper.usage.total_tokens = 50
        mock_decision_result.context_wrapper.usage.input_tokens = 40
        mock_decision_result.context_wrapper.usage.output_tokens = 10
        mock_decision_result.context_wrapper.usage.input_tokens_details = None
        mock_decision_result.context_wrapper.usage.output_tokens_details = None
        mock_decision_result.context_wrapper.usage.requests = 1
        mock_decision_result.context_wrapper.usage.request_usage_entries = []
        mock_runner_class.run = AsyncMock(return_value=mock_decision_result)

        # CRITICAL: buy_shares raises — this is what produces FAILED status.
        mock_buy.side_effect = RuntimeError("Broker rejected the order")

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name
        )

        # _execute_trade swallows the trade exception (sets FAILED status),
        # so execute_cycle returns normally rather than raising.
        await executor.execute_cycle(mcp_pool=mock_mcp_pool, force_trade=False)

        # Find the PHASE_COMPLETED broadcast call.
        completed_calls = [
            call_obj
            for call_obj in mock_broadcast.call_args_list
            if len(call_obj.args) >= 3 and call_obj.args[2] == PHASE_COMPLETED
        ]
        assert completed_calls, (
            f"Expected a PHASE_COMPLETED broadcast; got: "
            f"{[c.args for c in mock_broadcast.call_args_list]}"
        )

        # The pre-fix bug used 'Completed - No trades (HOLD decision)' for a
        # FAILED BUY because trade_id was None. After the fix the message must
        # exactly distinguish the FAILED case.
        final_completed = completed_calls[-1]
        # broadcast_status signature: (agent_id, agent_name, phase, message, progress, *, outcome=...)
        message_arg = final_completed.args[3]
        outcome_kwarg = final_completed.kwargs.get("outcome")
        assert message_arg == "Completed - Trade attempted but failed", (
            f"Wrong PHASE_COMPLETED message for FAILED BUY. Expected "
            f"'Completed - Trade attempted but failed', got: {message_arg!r}. "
            f"Full call: args={final_completed.args}, kwargs={final_completed.kwargs}"
        )
        assert outcome_kwarg == "Completed - Trade attempted but failed", (
            f"Wrong PHASE_COMPLETED outcome kwarg for FAILED BUY. Expected "
            f"'Completed - Trade attempted but failed', got: {outcome_kwarg!r}"
        )


def test_pricing_module_exports_model_pricing():
    from infra.pricing import _UNKNOWN_MODELS_WARNED, MODEL_PRICING, _load_model_pricing

    assert isinstance(
        MODEL_PRICING, dict
    ), "MODEL_PRICING must be a dict mapping model name to pricing tuple"
    assert (
        "gpt-4o-mini" in MODEL_PRICING
    ), "MODEL_PRICING should include gpt-4o-mini as a known model"
    assert isinstance(
        _UNKNOWN_MODELS_WARNED, set
    ), "_UNKNOWN_MODELS_WARNED must be a set for warning dedupe"
    assert callable(
        _load_model_pricing
    ), "_load_model_pricing must be callable (loads pricing from JSON)"


def test_telemetry_module_exports_functions():
    from infra.telemetry import extract_run_telemetry, extract_usage_metrics

    assert callable(
        extract_usage_metrics
    ), "extract_usage_metrics must be callable (SDK Usage → UsageMetrics)"
    assert callable(
        extract_run_telemetry
    ), "extract_run_telemetry must be callable (RunResult → tool calls + metrics)"
