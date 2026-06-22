"""End-to-end tests for ``phase_runner.run_cycle``.

Tests cross only the public Interface and mock at the system boundary:
* ``BackendClient`` — backend HTTP layer (shared singleton)
* SDK ``Runner.run`` and ``run_with_guardrail_retry`` — OpenAI calls
* Agent factories (``MarketAnalyst.create`` / ``DecisionMaker.create``) — agent construction

Internal collaborators (``Lifecycle``, telemetry helpers, prompt capture) are
NOT mocked — they're private to ``phase_runner`` and are tested transitively
through their observable effects on the BackendClient mock.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models import TradingDecision
from models.api_responses import AccountReport, RecentActivityResponse
from models.llm_output import CandidateStock, ResearchResponse, TradeAction, WebSource


def _make_account_report(agent_name: str = "Warren", balance: float = 100000.0) -> AccountReport:
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


def _make_sdk_result(final_output, model_name: str = "gpt-4o-mini"):
    """Minimal ``RunResult`` shape: ``new_items``, ``context_wrapper.usage``,
    ``final_output_as(T)``."""
    usage = MagicMock()
    usage.total_tokens = 100
    usage.input_tokens = 60
    usage.output_tokens = 40
    usage.requests = 1
    usage.input_tokens_details = None
    usage.output_tokens_details = None
    usage.request_usage_entries = []

    ctx_wrapper = MagicMock()
    ctx_wrapper.usage = usage

    result = MagicMock()
    result.new_items = []
    result.context_wrapper = ctx_wrapper
    result.final_output_as = lambda cls: final_output
    return result


def _make_guardrail_outcome(research_response):
    """The shape ``run_with_guardrail_retry`` returns on success."""
    sdk_result = _make_sdk_result(research_response)
    outcome = MagicMock()
    outcome.result = sdk_result
    outcome.attempts_used = 1
    outcome.last_issues = None
    outcome.outcome = "first_try"
    outcome.failed_output = None
    return outcome


@pytest.fixture
def mock_backend():
    """Patch ``get_backend_client`` at every import site (``cycle`` + ``_lifecycle``)
    to return the same ``MagicMock`` so assertions roll up across the cycle."""
    client = MagicMock()
    client.initialize_agent = AsyncMock(return_value=1)
    client.create_run = AsyncMock(return_value=123)
    client.update_phase = AsyncMock(return_value=None)
    client.complete_run = AsyncMock(return_value=None)
    client.record_phase_failure = AsyncMock(return_value=None)
    client.get_account_report = AsyncMock(return_value=_make_account_report("Warren"))
    client.get_recent_activity = AsyncMock(
        return_value=RecentActivityResponse(
            agentName="Warren", days=30, runs=[], totalRuns=0, totalTrades=0
        )
    )
    buy_result = MagicMock()
    buy_result.tradeId = 456
    sell_result = MagicMock()
    sell_result.tradeId = 789
    client.buy_shares = AsyncMock(return_value=buy_result)
    client.sell_shares = AsyncMock(return_value=sell_result)

    with (
        patch("phase_runner.cycle.get_backend_client", return_value=client),
        patch("phase_runner._lifecycle.get_backend_client", return_value=client),
        patch("phase_runner._lifecycle.broadcast_status"),
    ):
        yield client


@pytest.fixture
def mock_agents():
    """Stub Market Analyst + Decision Maker factories and the SDK call surface."""
    market_analyst = MagicMock()
    market_analyst.agent = MagicMock()
    market_analyst.agent.instructions = "Market analyst system prompt"
    market_analyst.build_prompt = MagicMock(return_value="research task prompt")
    market_analyst.model_name = "gpt-4o-mini"

    decision_maker = MagicMock()
    decision_maker.agent = MagicMock()
    decision_maker.agent.instructions = "Decision maker system prompt"
    decision_maker.build_prompt = MagicMock(return_value="decision task prompt")
    decision_maker.model_name = "gpt-4o-mini"

    with (
        patch(
            "phase_runner.cycle.MarketAnalyst.create",
            new=AsyncMock(return_value=market_analyst),
        ),
        patch(
            "phase_runner.cycle.DecisionMaker.create",
            new=AsyncMock(return_value=decision_maker),
        ),
    ):
        yield {"market_analyst": market_analyst, "decision_maker": decision_maker}


@pytest.fixture
def stub_sdk_calls():
    """Stub the SDK boundary: guardrail-wrapped research + bare Runner for decision."""
    research_response = _make_research_response()
    decision_obj = _make_buy_decision()

    guardrail_outcome = _make_guardrail_outcome(research_response)
    decision_result = _make_sdk_result(decision_obj)

    with (
        patch(
            "phase_runner.cycle.run_with_guardrail_retry",
            new=AsyncMock(return_value=guardrail_outcome),
        ) as p_research,
        patch(
            "phase_runner.cycle.Runner.run",
            new=AsyncMock(return_value=decision_result),
        ) as p_decision,
    ):
        yield {
            "research_call": p_research,
            "decision_call": p_decision,
            "research_response": research_response,
            "decision": decision_obj,
        }


class TestRunCycle:
    """Happy-path coverage through the public Interface."""

    async def test_buy_cycle_drives_lifecycle_and_executes_trade(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        mock_backend,
        mock_agents,
        stub_sdk_calls,
    ):
        from models.run_tracking import RunPhase
        from phase_runner import run_cycle

        await run_cycle(
            agent_id=sample_agent_id,
            name=sample_agent_name,
            agent_style=sample_agent_style,
            mcp_pool=MagicMock(),
            model_name=sample_model_name,
            force_trade=False,
        )

        # Lifecycle drove the full phase sequence through the backend.
        mock_backend.initialize_agent.assert_awaited_once_with(sample_agent_name, 100000.0)
        mock_backend.create_run.assert_awaited_once_with(sample_agent_id)
        phases_set = [c.args[1] for c in mock_backend.update_phase.await_args_list]
        assert RunPhase.RESEARCHING in phases_set
        assert RunPhase.DECIDING in phases_set
        assert RunPhase.TRADING in phases_set

        # Trade executed via BackendClient (NOT a trading_tools wrapper).
        mock_backend.buy_shares.assert_awaited_once_with(sample_agent_id, "AAPL", 100, run_id=123)

        # complete_run hit with the assembled payload.
        mock_backend.complete_run.assert_awaited_once()
        complete_args = mock_backend.complete_run.await_args.args
        assert complete_args[0] == 123  # run_id
        complete_data = complete_args[1]
        assert complete_data.execution.tradeId == 456
        assert complete_data.research.candidates == ["AAPL", "NVDA"]

        # FAILED path never triggered.
        assert RunPhase.FAILED not in phases_set

    async def test_hold_decision_skips_execution_and_completes(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        mock_backend,
        mock_agents,
        stub_sdk_calls,
    ):
        from phase_runner import run_cycle

        # Override the decision SDK call to return HOLD.
        stub_sdk_calls["decision_call"].return_value = _make_sdk_result(_make_hold_decision())

        await run_cycle(
            agent_id=sample_agent_id,
            name=sample_agent_name,
            agent_style=sample_agent_style,
            mcp_pool=MagicMock(),
            model_name=sample_model_name,
            force_trade=False,
        )

        mock_backend.buy_shares.assert_not_awaited()
        mock_backend.sell_shares.assert_not_awaited()
        mock_backend.complete_run.assert_awaited_once()
        # SKIPPED outcome shows up in the completion payload.
        complete_data = mock_backend.complete_run.await_args.args[1]
        from models.run_tracking import PhaseStatus

        assert complete_data.execution.status == PhaseStatus.SKIPPED
        assert complete_data.execution.tradeId is None

    async def test_failed_trade_completes_with_failed_status(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        mock_backend,
        mock_agents,
        stub_sdk_calls,
    ):
        from models.run_tracking import PhaseStatus
        from phase_runner import run_cycle

        mock_backend.buy_shares.side_effect = RuntimeError("Broker rejected the order")

        await run_cycle(
            agent_id=sample_agent_id,
            name=sample_agent_name,
            agent_style=sample_agent_style,
            mcp_pool=MagicMock(),
            model_name=sample_model_name,
            force_trade=False,
        )

        # complete_run still fires — FAILED is a normal cycle outcome, not a crash.
        mock_backend.complete_run.assert_awaited_once()
        complete_data = mock_backend.complete_run.await_args.args[1]
        assert complete_data.execution.status == PhaseStatus.FAILED
        assert complete_data.execution.tradeId is None
        assert complete_data.execution.errorDetails == "Broker rejected the order"

    async def test_model_name_defaults_to_config_when_none(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        mock_backend,
        mock_agents,
        stub_sdk_calls,
    ):
        from config import config
        from phase_runner import run_cycle

        # MarketAnalyst.create gets called with the resolved model name.
        with patch(
            "phase_runner.cycle.MarketAnalyst.create",
            new=AsyncMock(return_value=mock_agents["market_analyst"]),
        ) as p_create:
            await run_cycle(
                agent_id=sample_agent_id,
                name=sample_agent_name,
                agent_style=sample_agent_style,
                mcp_pool=MagicMock(),
                model_name=None,
                force_trade=False,
            )
            assert p_create.await_args.kwargs["model_name"] == config.OPENAI_MODEL

    async def test_force_trade_propagates_to_decision_context(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        mock_backend,
        mock_agents,
        stub_sdk_calls,
    ):
        from phase_runner import run_cycle

        await run_cycle(
            agent_id=sample_agent_id,
            name=sample_agent_name,
            agent_style=sample_agent_style,
            mcp_pool=MagicMock(),
            model_name=sample_model_name,
            force_trade=True,
        )

        # build_prompt on DecisionMaker received a DecisionContext with force_trade=True.
        build_call = mock_agents["decision_maker"].build_prompt.call_args
        assert build_call.args[0].force_trade is True


class TestErrorPath:
    """Cycle never raises; failures route through Lifecycle.fail and downstream phases stop."""

    async def test_research_failure_marks_run_failed_and_no_decision(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        mock_backend,
        mock_agents,
        stub_sdk_calls,
    ):
        from models.run_tracking import RunPhase
        from phase_runner import run_cycle

        stub_sdk_calls["research_call"].side_effect = RuntimeError("research blew up")

        # Cycle does not raise.
        await run_cycle(
            agent_id=sample_agent_id,
            name=sample_agent_name,
            agent_style=sample_agent_style,
            mcp_pool=MagicMock(),
            model_name=sample_model_name,
            force_trade=False,
        )

        # Lifecycle.fail wrote a FAILED phase update with the error message.
        phases_seen = mock_backend.update_phase.await_args_list
        failed_calls = [c for c in phases_seen if c.args[1] == RunPhase.FAILED]
        assert len(failed_calls) == 1
        assert failed_calls[0].kwargs.get("error_message")

        # Decision never ran.
        stub_sdk_calls["decision_call"].assert_not_awaited()
        # Trade never ran.
        mock_backend.buy_shares.assert_not_awaited()
        # complete_run never fires on the failure path — only on the happy path.
        mock_backend.complete_run.assert_not_awaited()

    async def test_research_guardrail_exhausted_persists_phase_failure_stub(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        mock_backend,
        mock_agents,
        stub_sdk_calls,
    ):
        from agents.exceptions import OutputGuardrailTripwireTriggered

        from phase_runner import run_cycle

        outcome_obj = MagicMock()
        outcome_obj.attempts_used = 3
        outcome_obj.outcome = "exhausted"
        tripwire = OutputGuardrailTripwireTriggered(MagicMock())
        tripwire.guardrail_outcome = outcome_obj
        stub_sdk_calls["research_call"].side_effect = tripwire

        await run_cycle(
            agent_id=sample_agent_id,
            name=sample_agent_name,
            agent_style=sample_agent_style,
            mcp_pool=MagicMock(),
            model_name=sample_model_name,
            force_trade=False,
        )

        mock_backend.record_phase_failure.assert_awaited_once()
        call = mock_backend.record_phase_failure.await_args
        assert call.args[0] == 123  # run_id
        assert call.args[1] == "RESEARCH"
        assert call.args[2] is outcome_obj

    async def test_lifecycle_fail_cleanup_error_does_not_propagate(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        mock_backend,
        mock_agents,
        stub_sdk_calls,
    ):
        """Defense in depth: even if Lifecycle.fail's own update_phase write fails,
        run_cycle still returns cleanly."""
        from phase_runner import run_cycle

        stub_sdk_calls["research_call"].side_effect = RuntimeError("research boom")

        # The FAILED update_phase write (inside Lifecycle.fail) raises.
        async def update_phase_side_effect(run_id, phase, **kwargs):
            from models.run_tracking import RunPhase

            if phase == RunPhase.FAILED:
                raise RuntimeError("cleanup boom")
            return None

        mock_backend.update_phase.side_effect = update_phase_side_effect

        # Must not raise.
        await run_cycle(
            agent_id=sample_agent_id,
            name=sample_agent_name,
            agent_style=sample_agent_style,
            mcp_pool=MagicMock(),
            model_name=sample_model_name,
            force_trade=False,
        )
