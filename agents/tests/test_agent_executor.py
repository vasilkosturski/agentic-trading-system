from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

import agent_executor
from agent_executor import (
    _fetch_account_data,
    _fetch_recent_activity,
    _handle_cycle_error,
    execute_cycle,
)
from backend.run_lifecycle import RunLifecycle
from models import TradingDecision
from models.api_responses import AccountReport, RecentActivityResponse
from models.llm_output import CandidateStock, ResearchResponse, TradeAction, WebSource
from models.orchestration import (
    AccountData,
    CycleResult,
    DecisionResult,
    ExecutionResult,
    ResearchResult,
    RunContext,
)
from models.run_tracking import PhaseStatus


@pytest.fixture
def mock_mcp_pool_simple():
    return MagicMock()


def _make_account_report(agent_name: str, balance: float = 100000.0) -> AccountReport:
    return AccountReport(
        agentName=agent_name,
        balance=balance,
        holdingsValue=0.0,
        totalPortfolioValue=balance,
        initialBalance=balance,
        totalProfitLoss=0.0,
        profitLossPercent=0.0,
        holdingsCount=0,
        transactionCount=0,
        holdings=[],
    )


def _make_research_response() -> ResearchResponse:
    return ResearchResponse(
        candidates=[
            CandidateStock(symbol="AAPL", price=185.0),
            CandidateStock(symbol="NVDA", price=145.0),
        ],
        summary="2 strong candidates",
        webSources=[
            WebSource(title="Article 1", url="https://example.com/1"),
            WebSource(title="Article 2", url="https://example.com/2"),
        ],
    )


def _make_buy_decision() -> TradingDecision:
    return TradingDecision(
        action=TradeAction.BUY,
        symbol="AAPL",
        quantity=100,
        rationale="Strong growth",
        portfolioContext="Room for new positions.",
        historicalContext="No prior AAPL trades.",
        researchContext="Strong fundamentals across sector.",
    )


def _make_hold_decision() -> TradingDecision:
    return TradingDecision(
        action=TradeAction.HOLD,
        symbol="",
        quantity=0,
        rationale="Wait and see",
        portfolioContext="Already balanced.",
        historicalContext="Prior trades show stability.",
        researchContext="No compelling opportunity.",
    )


@pytest.fixture
def patched_phases():
    """Patch all four phase modules + backend access points so execute_cycle
    can be driven end-to-end without touching the agent stack."""
    research_response = _make_research_response()
    decision = _make_buy_decision()
    recent_activity = RecentActivityResponse(
        agentName="Warren", days=30, runs=[], totalRuns=0, totalTrades=0
    )

    research_result = ResearchResult(
        research_response=research_response,
        candidates=["AAPL", "NVDA"],
        sources=[],
        notes="2 strong candidates",
        tool_calls=[],
        usage_metrics=None,
        research_latency_ms=42,
    )
    decision_result = DecisionResult(
        decision=decision,
        decision_start_time=datetime.now(),
        tool_calls=[],
        usage_metrics=None,
    )
    execution_result = ExecutionResult(
        execution_status=PhaseStatus.COMPLETED,
        trade_id=456,
        execution_error=None,
    )

    with (
        patch(
            "agent_executor.run_research_phase", new=AsyncMock(return_value=research_result)
        ) as p_research,
        patch(
            "agent_executor.run_decision_phase", new=AsyncMock(return_value=decision_result)
        ) as p_decision,
        patch(
            "agent_executor.run_execution_phase", new=AsyncMock(return_value=execution_result)
        ) as p_execution,
        patch(
            "agent_executor.run_finalization_phase", new=AsyncMock(return_value=None)
        ) as p_finalization,
        patch(
            "agent_executor._get_account_report_raw",
            new=AsyncMock(return_value=_make_account_report("Warren")),
        ) as p_acct,
        patch("agent_executor.get_backend_client") as p_get_client,
    ):
        mock_client = MagicMock()
        mock_client.get_recent_activity = AsyncMock(return_value=recent_activity)
        p_get_client.return_value = mock_client

        # Lifecycle: stub start to return a run_id and the rest to no-ops
        # so the run-tracking layer is exercised at its interface, not its
        # full HTTP stack.
        with (
            patch.object(RunLifecycle, "start", new=AsyncMock(return_value=123)),
            patch.object(RunLifecycle, "transition_to_deciding", new=AsyncMock(return_value=None)),
            patch.object(RunLifecycle, "transition_to_trading", new=AsyncMock(return_value=None)),
            patch.object(RunLifecycle, "complete", new=AsyncMock(return_value=None)),
            patch.object(RunLifecycle, "fail", new=AsyncMock(return_value=None)),
        ):
            yield {
                "research_phase": p_research,
                "decision_phase": p_decision,
                "execution_phase": p_execution,
                "finalization_phase": p_finalization,
                "account_report": p_acct,
                "get_backend_client": p_get_client,
                "backend_client": mock_client,
                "research_result": research_result,
                "decision_result": decision_result,
                "execution_result": execution_result,
                "recent_activity": recent_activity,
                "decision": decision,
            }


class TestExecuteCycle:
    async def test_happy_path_runs_phases_in_order_and_returns_cycle_result(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        mock_mcp_pool_simple,
        patched_phases,
    ):
        result = await execute_cycle(
            agent_id=sample_agent_id,
            name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name=sample_model_name,
            mcp_pool=mock_mcp_pool_simple,
            force_trade=False,
        )

        assert isinstance(result, CycleResult)
        assert result.decision == patched_phases["decision"]
        assert result.run_id == 123
        assert result.trade_count == 1

        patched_phases["research_phase"].assert_awaited_once()
        patched_phases["decision_phase"].assert_awaited_once()
        patched_phases["execution_phase"].assert_awaited_once()
        patched_phases["finalization_phase"].assert_awaited_once()

    async def test_hold_decision_skips_execution_phase(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        mock_mcp_pool_simple,
        patched_phases,
    ):
        hold_decision_result = DecisionResult(
            decision=_make_hold_decision(),
            decision_start_time=datetime.now(),
            tool_calls=[],
            usage_metrics=None,
        )
        patched_phases["decision_phase"].return_value = hold_decision_result

        result = await execute_cycle(
            agent_id=sample_agent_id,
            name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name=sample_model_name,
            mcp_pool=mock_mcp_pool_simple,
            force_trade=False,
        )

        patched_phases["execution_phase"].assert_not_awaited()
        patched_phases["finalization_phase"].assert_awaited_once()
        assert result.trade_count == 0
        assert result.decision.action == "HOLD"

    async def test_failed_buy_yields_trade_count_zero(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        mock_mcp_pool_simple,
        patched_phases,
    ):
        patched_phases["execution_phase"].return_value = ExecutionResult(
            execution_status=PhaseStatus.FAILED,
            trade_id=None,
            execution_error="Broker rejected the order",
        )

        result = await execute_cycle(
            agent_id=sample_agent_id,
            name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name=sample_model_name,
            mcp_pool=mock_mcp_pool_simple,
            force_trade=False,
        )

        assert result.trade_count == 0
        patched_phases["finalization_phase"].assert_awaited_once()

    async def test_model_name_defaults_to_config_when_none(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        mock_mcp_pool_simple,
        patched_phases,
    ):
        from config import config

        await execute_cycle(
            agent_id=sample_agent_id,
            name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name=None,
            mcp_pool=mock_mcp_pool_simple,
            force_trade=False,
        )

        # The decision phase receives ctx with model_name resolved.
        kwargs = patched_phases["decision_phase"].await_args.kwargs
        ctx_passed = kwargs["ctx"]
        assert ctx_passed.model_name == config.OPENAI_MODEL


class TestFetchData:
    async def test_fetch_account_data_returns_account_data(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_balance,
        sample_holdings,
    ):
        report = AccountReport(
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

        with patch(
            "agent_executor._get_account_report_raw", new=AsyncMock(return_value=report)
        ) as mock_get_report:
            result = await _fetch_account_data(sample_agent_id)

        assert isinstance(result, AccountData)
        assert result.balance == sample_balance
        assert result.holdings == sample_holdings
        mock_get_report.assert_awaited_once_with(sample_agent_id)

    async def test_fetch_account_data_propagates_backend_error(self, sample_agent_id):
        from infra.exceptions import BackendAPIError

        with patch(
            "agent_executor._get_account_report_raw",
            new=AsyncMock(side_effect=BackendAPIError("boom", status_code=500)),
        ):
            with pytest.raises(BackendAPIError) as exc_info:
                await _fetch_account_data(sample_agent_id)

        assert exc_info.value.status_code == 500

    async def test_fetch_recent_activity_calls_client_with_lookback(
        self,
        sample_agent_id,
        sample_recent_activity,
    ):
        mock_client = MagicMock()
        mock_client.get_recent_activity = AsyncMock(return_value=sample_recent_activity)

        with patch("agent_executor.get_backend_client", return_value=mock_client):
            result = await _fetch_recent_activity(sample_agent_id)

        assert isinstance(result, RecentActivityResponse)
        assert result == sample_recent_activity
        mock_client.get_recent_activity.assert_awaited_once_with(
            sample_agent_id, days=agent_executor.RECENT_ACTIVITY_LOOKBACK_DAYS
        )

    async def test_fetch_recent_activity_propagates_backend_error(self, sample_agent_id):
        from infra.exceptions import BackendAPIError

        mock_client = MagicMock()
        mock_client.get_recent_activity = AsyncMock(
            side_effect=BackendAPIError("recent_activity boom", status_code=502)
        )

        with patch("agent_executor.get_backend_client", return_value=mock_client):
            with pytest.raises(BackendAPIError) as exc_info:
                await _fetch_recent_activity(sample_agent_id)

        assert exc_info.value.status_code == 502


class TestErrorHandling:
    async def test_execute_cycle_research_failure_invokes_lifecycle_fail_and_reraises(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        mock_mcp_pool_simple,
        patched_phases,
    ):
        boom = RuntimeError("research blew up")
        patched_phases["research_phase"].side_effect = boom

        with pytest.raises(RuntimeError, match="research blew up"):
            await execute_cycle(
                agent_id=sample_agent_id,
                name=sample_agent_name,
                agent_style=sample_agent_style,
                model_name=sample_model_name,
                mcp_pool=mock_mcp_pool_simple,
                force_trade=False,
            )

        # lifecycle.fail is patched class-wide via patched_phases; verify it
        # was awaited with the original exception.
        RunLifecycle.fail.assert_awaited_once()
        call = RunLifecycle.fail.await_args
        # Patching at class level via patch.object replaces the function
        # descriptor with an AsyncMock, so `self` is NOT auto-bound — the
        # AsyncMock sees positional args (run_id, error).
        assert call.args[-1] is boom

        # Downstream phases must not run.
        patched_phases["decision_phase"].assert_not_awaited()
        patched_phases["execution_phase"].assert_not_awaited()
        patched_phases["finalization_phase"].assert_not_awaited()

    async def test_handle_cycle_error_without_ctx_calls_fail_with_none_run_id(self):
        mock_lifecycle = Mock(spec=RunLifecycle)
        mock_lifecycle.fail = AsyncMock()
        err = RuntimeError("init failure")

        await _handle_cycle_error(err, ctx=None, lifecycle=mock_lifecycle)

        mock_lifecycle.fail.assert_awaited_once_with(None, err)

    async def test_handle_cycle_error_with_ctx_passes_run_id(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        sample_recent_activity,
    ):
        mock_lifecycle = Mock(spec=RunLifecycle)
        mock_lifecycle.fail = AsyncMock()

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

        await _handle_cycle_error(err, ctx=ctx, lifecycle=mock_lifecycle)

        mock_lifecycle.fail.assert_awaited_once_with(777, err)

    async def test_handle_cycle_error_swallows_lifecycle_fail_exception(self):
        # Defense in depth: if RunLifecycle.fail itself raises, the helper
        # must NOT propagate the cleanup error — the caller re-raises the
        # original cycle exception.
        mock_lifecycle = Mock(spec=RunLifecycle)
        mock_lifecycle.fail = AsyncMock(side_effect=RuntimeError("cleanup boom"))
        err = RuntimeError("cycle boom")

        result = await _handle_cycle_error(err, ctx=None, lifecycle=mock_lifecycle)

        assert result is None
        mock_lifecycle.fail.assert_awaited_once_with(None, err)


class TestPhaseRouting:
    async def test_run_context_is_built_and_threaded_to_each_phase(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        mock_mcp_pool_simple,
        patched_phases,
    ):
        await execute_cycle(
            agent_id=sample_agent_id,
            name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name=sample_model_name,
            mcp_pool=mock_mcp_pool_simple,
            force_trade=False,
        )

        research_ctx = patched_phases["research_phase"].await_args.kwargs["ctx"]
        decision_ctx = patched_phases["decision_phase"].await_args.kwargs["ctx"]

        assert research_ctx is decision_ctx
        assert isinstance(research_ctx, RunContext)
        assert research_ctx.run_id == 123
        assert research_ctx.agent_id == sample_agent_id
        assert research_ctx.agent_name == sample_agent_name
        assert research_ctx.agent_style == sample_agent_style
        assert research_ctx.model_name == sample_model_name
        # Account data populated from the patched backend.
        assert research_ctx.balance == 100000.0
        assert research_ctx.holdings == []
        # Recent activity threaded through.
        assert research_ctx.recent_activity == patched_phases["recent_activity"]

    async def test_phase_call_ordering_research_before_decision_before_execution(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        mock_mcp_pool_simple,
        patched_phases,
    ):
        call_log: list[str] = []

        async def record_research(*args, **kwargs):
            call_log.append("research")
            return patched_phases["research_result"]

        async def record_decision(*args, **kwargs):
            call_log.append("decision")
            return patched_phases["decision_result"]

        async def record_execution(*args, **kwargs):
            call_log.append("execution")
            return patched_phases["execution_result"]

        async def record_finalization(*args, **kwargs):
            call_log.append("finalization")
            return None

        patched_phases["research_phase"].side_effect = record_research
        patched_phases["decision_phase"].side_effect = record_decision
        patched_phases["execution_phase"].side_effect = record_execution
        patched_phases["finalization_phase"].side_effect = record_finalization

        await execute_cycle(
            agent_id=sample_agent_id,
            name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name=sample_model_name,
            mcp_pool=mock_mcp_pool_simple,
            force_trade=False,
        )

        assert call_log == ["research", "decision", "execution", "finalization"]

    async def test_force_trade_flag_propagates_to_decision_phase(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        mock_mcp_pool_simple,
        patched_phases,
    ):
        await execute_cycle(
            agent_id=sample_agent_id,
            name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name=sample_model_name,
            mcp_pool=mock_mcp_pool_simple,
            force_trade=True,
        )

        kwargs = patched_phases["decision_phase"].await_args.kwargs
        assert kwargs["force_trade"] is True

    async def test_execution_phase_receives_decision_and_run_id(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        mock_mcp_pool_simple,
        patched_phases,
    ):
        await execute_cycle(
            agent_id=sample_agent_id,
            name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name=sample_model_name,
            mcp_pool=mock_mcp_pool_simple,
            force_trade=False,
        )

        kwargs = patched_phases["execution_phase"].await_args.kwargs
        assert kwargs["run_id"] == 123
        assert kwargs["agent_id"] == sample_agent_id
        assert kwargs["agent_name"] == sample_agent_name
        assert kwargs["decision"] == patched_phases["decision_phase"].return_value.decision
