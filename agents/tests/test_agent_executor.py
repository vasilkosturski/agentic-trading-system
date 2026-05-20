"""Tests for AgentExecutor with explicit phase returns."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from agent_executor import AgentExecutor
from phases.research_phase import run_research_phase
from phases.decision_phase import run_decision_phase
from run_lifecycle import RunLifecycle
from models.investment_style import InvestmentStyle
from models.orchestration import (
    CycleResult,
    RunContext,
    AccountData,
    ResearchResult,
    DecisionResult,
)
from models.llm_output import CandidateStock, TradingDecision, ResearchResponse, WebSource
from models.run_tracking import TradeDecision


# ============================================================================
# Fixtures
# ============================================================================

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
    """Sample recent activity for testing (typed Pydantic model)."""
    from models.api_responses import RecentActivityResponse, ActivityRun, ActivityTrade
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
                trades=[
                    ActivityTrade(type="BUY", symbol="NVDA", quantity=50, price=145.0)
                ]
            )
        ],
        totalRuns=1,
        totalTrades=1
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


# ============================================================================
# Test: Initialization
# ============================================================================

class TestAgentExecutorInitialization:
    """Test AgentExecutor initialization."""

    def test_init(self, sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name):
        """Test executor initializes with correct attributes."""
        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name
        )

        assert executor.agent_id == sample_agent_id
        assert executor.name == sample_agent_name
        assert executor.agent_style == sample_agent_style
        assert executor.model_name == sample_model_name


# ============================================================================
# Test: Fetch Account Data
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorFetchData:
    """Test data fetching methods."""

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
        """Test _fetch_account_data returns AccountData."""
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
        """_fetch_account_data must propagate BackendAPIError unchanged.

        Pins the contract that the helper no longer wraps backend failures as
        RuntimeError — matching the sibling _fetch_recent_activity style and
        the file's fail-fast philosophy. The typed exception (with status_code)
        must survive so callers and logs see the real cause.
        """
        from exceptions import BackendAPIError

        mock_get_report.side_effect = BackendAPIError(
            "GET /api/agents/1/account-report failed", status_code=500
        )

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style
        )

        with pytest.raises(BackendAPIError) as exc_info:
            await executor._fetch_account_data(sample_agent_id)

        # Status code must survive — proves the typed exception was not
        # rewrapped as a RuntimeError (which would drop status_code).
        assert exc_info.value.status_code == 500


# ============================================================================
# Test: Market Analyst
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorMarketAnalyst:
    """Test _run_market_analyst method."""

    @patch("phases.research_phase.MarketAnalyst")
    @patch("guardrail_retry.Runner")
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
        """Test _run_market_analyst returns ResearchResult."""
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

        # No AgentExecutor instance needed — run_research_phase is a
        # module-level function (Task 6 of the decomposition plan).

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


# ============================================================================
# Test: Full Cycle
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorFullCycle:
    """Test full execute_cycle."""

    @patch("run_lifecycle.complete_run")
    @patch("phases.execution_phase.buy_shares")
    @patch("phases.decision_phase.DecisionMaker")
    @patch("phases.research_phase.MarketAnalyst")
    @patch("phases.decision_phase.Runner")
    @patch("guardrail_retry.Runner")
    @patch("run_lifecycle.update_phase")
    @patch("run_lifecycle.create_run")
    @patch("agent_executor.get_backend_client")
    @patch("agent_executor._get_account_report_raw")
    @patch("run_lifecycle.initialize_agent")
    @patch("run_lifecycle.broadcast_status")
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
        """Test full cycle with successful BUY decision."""
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


# ============================================================================
# Test: Error-path branches (I11) — BackendAPIError, MaxTurnsExceeded,
#                                   _handle_cycle_error
# ============================================================================


@pytest.mark.asyncio
class TestAgentExecutorErrorPaths:
    """Error-path coverage for AgentExecutor (I11).

    These tests exercise branches not covered by the happy-path tests above:
      * ``execute_cycle`` routes phase errors through ``_handle_cycle_error``
        which broadcasts an ERROR status and re-raises.
      * ``execute_cycle`` propagates ``MaxTurnsExceeded`` from the market
        analyst run with the run marked FAILED.
      * ``_handle_cycle_error`` with ``ctx=None`` (failure before context was
        built) must NOT touch ``update_phase`` since no run exists yet.
      * ``_handle_cycle_error`` swallows secondary cleanup errors from
        ``update_phase`` so the original exception is still re-raised.
    """

    @patch("run_lifecycle.update_phase")
    @patch("run_lifecycle.complete_run")
    @patch("run_lifecycle.create_run")
    @patch("agent_executor.get_backend_client")
    @patch("agent_executor._get_account_report_raw")
    @patch("run_lifecycle.initialize_agent")
    @patch("run_lifecycle.broadcast_status")
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
        """If _fetch_recent_activity raises BackendAPIError, the orchestrator
        must call _handle_cycle_error (PHASE_ERROR broadcast + mark FAILED)
        and re-raise the original exception."""
        from exceptions import BackendAPIError
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
            call for call in mock_broadcast.call_args_list
            if call.args[2] == "FAILED"
        ]
        assert error_broadcasts, "expected PHASE_ERROR broadcast on failure"
        # complete_run must NOT have been called — the orchestrator deliberately
        # avoids overriding a failed run back to COMPLETED.
        mock_complete_run.assert_not_called()

    @patch("run_lifecycle.complete_run")
    @patch("phases.decision_phase.DecisionMaker")
    @patch("phases.research_phase.MarketAnalyst")
    @patch("guardrail_retry.Runner")
    @patch("run_lifecycle.update_phase")
    @patch("run_lifecycle.create_run")
    @patch("agent_executor.get_backend_client")
    @patch("agent_executor._get_account_report_raw")
    @patch("run_lifecycle.initialize_agent")
    @patch("run_lifecycle.broadcast_status")
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
        """MaxTurnsExceeded raised inside the Market Analyst run must propagate
        out of execute_cycle after _handle_cycle_error records the failure."""
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

        # Guardrail retry runner blows up with MaxTurnsExceeded.
        mock_guardrail_runner_class.run = AsyncMock(
            side_effect=MaxTurnsExceeded("agent looped too long")
        )

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name
        )

        with pytest.raises(MaxTurnsExceeded):
            await executor.execute_cycle(mcp_pool=mock_mcp_pool, force_trade=False)

        # The error must have been recorded against the existing run (run_id=555)
        # via update_phase(FAILED, error_message=...). Find that call.
        failed_calls = [
            call for call in mock_update_phase.call_args_list
            if len(call.args) >= 2 and getattr(call.args[1], "name", None) == "FAILED"
        ]
        assert failed_calls, "expected update_phase(run_id, RunPhase.FAILED) on MaxTurnsExceeded"
        # complete_run must NOT be called — failed runs are not "completed".
        mock_complete_run.assert_not_called()
        # DecisionMaker.create must NOT have been called — research crashed first.
        mock_decision_maker_class.create.assert_not_called()

    async def test_handle_cycle_error_without_ctx_skips_update_phase(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
    ):
        """When ctx is None (failure before run creation), _handle_cycle_error
        must delegate to lifecycle.fail with run_id=None (lifecycle handles the
        skip-update-phase contract — verified separately in test_run_lifecycle.py)."""
        mock_lifecycle = Mock(spec=RunLifecycle)
        mock_lifecycle.fail = AsyncMock()

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style
        )
        err = RuntimeError("init failure")

        await executor._handle_cycle_error(err, ctx=None, lifecycle=mock_lifecycle)

        # Boundary contract: _handle_cycle_error must call lifecycle.fail with
        # run_id=None when ctx is None.
        mock_lifecycle.fail.assert_called_once_with(None, err)

    async def test_handle_cycle_error_swallows_cleanup_error(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        sample_recent_activity,
    ):
        """_handle_cycle_error delegates to lifecycle.fail. The actual
        swallowed-cleanup-error contract lives inside RunLifecycle.fail and is
        verified by test_run_lifecycle.py:test_fail_swallows_cleanup_errors_and_does_not_raise.
        This test pins the boundary: _handle_cycle_error calls lifecycle.fail
        with the right args and does not raise."""
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

        # Must return normally — never raise from _handle_cycle_error itself.
        await executor._handle_cycle_error(err, ctx=ctx, lifecycle=mock_lifecycle)

        mock_lifecycle.fail.assert_called_once_with(777, err)


# ============================================================================
# Test: Module-level constants (refactor #1 — promote magic numbers)
# ============================================================================
#
# These tests pin the contract that six magic numbers in agent_executor.py have
# been promoted to module-level UPPER_CASE constants and that the call sites
# reference those identifiers (not raw integer literals). The change is a pure
# naming refactor — values are identical to the literals previously inlined.

class TestAgentExecutorModuleConstants:
    """Pin module-level constants required by the magic-numbers refactor."""

    def test_max_positions_constant_value(self):
        """MAX_POSITIONS = 10 (used at market analyst + decision maker call sites)."""
        import agent_executor
        assert agent_executor.MAX_POSITIONS == 10

    def test_research_max_attempts_constant_value(self):
        """RESEARCH_MAX_ATTEMPTS = 3 (used by run_with_guardrail_retry)."""
        import agent_executor
        assert agent_executor.RESEARCH_MAX_ATTEMPTS == 3

    def test_agent_max_turns_constant_value(self):
        """AGENT_MAX_TURNS = 30 (used by guardrail retry + Runner.run)."""
        import agent_executor
        assert agent_executor.AGENT_MAX_TURNS == 30

    def test_recent_activity_lookback_days_constant_value(self):
        """RECENT_ACTIVITY_LOOKBACK_DAYS = 30 (used by get_recent_activity)."""
        import agent_executor
        assert agent_executor.RECENT_ACTIVITY_LOOKBACK_DAYS == 30

    def test_max_reasoning_field_len_constant_value(self):
        """MAX_REASONING_FIELD_LEN = 2000 (truncation of reasoning fields)."""
        import agent_executor
        assert agent_executor.MAX_REASONING_FIELD_LEN == 2000

    def test_max_error_message_len_constant_value(self):
        """MAX_ERROR_MESSAGE_LEN = 500 (truncation of error message)."""
        import agent_executor
        assert agent_executor.MAX_ERROR_MESSAGE_LEN == 500

    def test_call_sites_use_named_constants_not_literals(self):
        """The six call sites listed in the task description must reference the
        named constants by identifier — not inline the integer literal.

        This guards against a partial refactor where the constant is defined
        but a call site still has the raw number.

        Note: Task 6 of the decomposition lifted _run_market_analyst into
        phases/research_phase.py — the max_attempts=RESEARCH_MAX_ATTEMPTS
        call site moved with it. Task 7 lifted _run_decision_maker into
        phases/decision_phase.py — the max_positions=MAX_POSITIONS and
        max_turns=AGENT_MAX_TURNS call sites at the decision-maker site
        moved with it. Task 9 lifted _finalize_run into
        phases/finalization.py — the [:MAX_REASONING_FIELD_LEN] call
        sites moved with it. The test now scans all four modules so the
        invariant survives the phase-module extractions.
        """
        import inspect
        import agent_executor
        from phases import research_phase, decision_phase, finalization

        source = (
            inspect.getsource(agent_executor)
            + inspect.getsource(research_phase)
            + inspect.getsource(decision_phase)
            + inspect.getsource(finalization)
        )

        # Call-site fragments that must appear verbatim after the refactor.
        # If any of these are missing, a call site is still using a literal.
        # Note: [:MAX_ERROR_MESSAGE_LEN] was removed when _handle_cycle_error
        # was collapsed to delegate to RunLifecycle.fail — the truncation now
        # lives in run_lifecycle.py (verified by test_run_lifecycle.py).
        required_fragments = [
            "max_positions=MAX_POSITIONS",  # _run_market_analyst + _run_decision_maker
            "max_attempts=RESEARCH_MAX_ATTEMPTS",  # run_with_guardrail_retry
            "max_turns=AGENT_MAX_TURNS",  # guardrail retry + Runner.run
            "days=RECENT_ACTIVITY_LOOKBACK_DAYS",  # get_recent_activity
            "[:MAX_REASONING_FIELD_LEN]",  # four reasoning truncations
        ]
        for fragment in required_fragments:
            assert fragment in source, (
                f"Expected fragment {fragment!r} not found in agent_executor.py — "
                f"a call site is still using a raw integer literal."
            )

        # And the inverse: the specific literal-bearing patterns the refactor
        # eliminates must NOT appear anywhere in the source.
        forbidden_fragments = [
            "max_positions=10",
            "max_attempts=3",
            "max_turns=30",
            "days=30",
            "[:2000]",
            "[:500]",
        ]
        for fragment in forbidden_fragments:
            assert fragment not in source, (
                f"Forbidden literal fragment {fragment!r} still present in "
                f"agent_executor.py — refactor incomplete."
            )


# ============================================================================
# Test: Class docstring — Concurrency clarification (refactor #2)
# ============================================================================
#
# These tests pin the contract that the AgentExecutor class docstring carries
# an explicit "Concurrency:" block stating single-cycle-per-instance semantics
# and pointing readers at the supported parallelism model (one executor per
# agent fanned out via asyncio.gather in trading_system.py). The change is
# pure documentation — runtime behavior is unchanged.

class TestAgentExecutorClassDocstringConcurrency:
    """Pin the Concurrency block required by the docstring-tightening refactor."""

    def test_class_docstring_has_concurrency_section(self):
        """A 'Concurrency:' section header must be present in the class docstring."""
        doc = AgentExecutor.__doc__
        assert doc is not None, "AgentExecutor must have a class docstring"
        assert "Concurrency:" in doc, (
            "AgentExecutor class docstring is missing the 'Concurrency:' "
            "section header — readers can wrongly infer thread-safety."
        )

    def test_class_docstring_states_single_cycle_semantics(self):
        """Docstring must explicitly state single-cycle-per-instance-at-a-time."""
        doc = AgentExecutor.__doc__ or ""
        assert "single cycle per executor instance at a time" in doc, (
            "Concurrency block must spell out 'single cycle per executor "
            "instance at a time' so the constraint is unambiguous."
        )

    def test_class_docstring_warns_against_concurrent_execute_cycle(self):
        """Docstring must explicitly forbid concurrent execute_cycle on one instance."""
        doc = AgentExecutor.__doc__ or ""
        assert "Do not call" in doc and "execute_cycle" in doc, (
            "Concurrency block must explicitly warn against concurrent "
            "execute_cycle calls on the same instance."
        )

    def test_class_docstring_references_supported_parallelism_model(self):
        """Docstring must reference trading_system.py and asyncio.gather fan-out."""
        doc = AgentExecutor.__doc__ or ""
        assert "trading_system.py" in doc, (
            "Concurrency block must reference trading_system.py as the "
            "supported parallelism pattern so future readers have a concrete "
            "example to follow."
        )
        assert "asyncio.gather" in doc, (
            "Concurrency block must call out asyncio.gather as the fan-out "
            "primitive used by the orchestrator."
        )

    def test_class_docstring_preserves_existing_content(self):
        """All pre-existing docstring content must be preserved verbatim."""
        doc = AgentExecutor.__doc__ or ""
        # Opening summary
        assert "Handles agent execution orchestration for trading cycles." in doc
        # 'Uses Trading Runs API for tracking:' block + each phase
        assert "Uses Trading Runs API for tracking:" in doc
        for phase in (
            "INITIALIZING",
            "RESEARCHING",
            "DECIDING",
            "TRADING",
            "COMPLETED",
            "ERROR",
        ):
            assert phase in doc, f"Phase {phase!r} missing from class docstring"
        # 'Data Flow:' block + its three bullets
        assert "Data Flow:" in doc
        assert "RunContext created at start" in doc
        assert "Context passed through all operations explicitly" in doc
        assert "No instance variables for per-run state" in doc

    def test_concurrency_block_appears_after_data_flow_block(self):
        """The new 'Concurrency:' block must follow the existing 'Data Flow:' block.

        Ordering matters for readability: the existing content lays out what
        the class does and how data flows; the Concurrency block then clarifies
        what those claims do and do not guarantee.
        """
        doc = AgentExecutor.__doc__ or ""
        data_flow_idx = doc.find("Data Flow:")
        concurrency_idx = doc.find("Concurrency:")
        assert data_flow_idx >= 0, "Data Flow block missing"
        assert concurrency_idx >= 0, "Concurrency block missing"
        assert concurrency_idx > data_flow_idx, (
            "Concurrency block must appear AFTER the Data Flow block, not "
            "before — Data Flow's 'No instance variables' bullet is the line "
            "the Concurrency block is qualifying."
        )


# ============================================================================
# Test: Cycle-start/end print() -> logger.info migration (refactor #3)
# ============================================================================
#
# These tests pin the contract that the two outlier print() calls in
# agent_executor.py (cycle start with 🤖 emoji and cycle end with ✅ emoji)
# have been converted to logger.info(...) so the events flow through Python's
# logging infrastructure (file rotators, JSON serializers, log shippers) like
# every other observable event in the module.

class TestAgentExecutorCycleLoggerMigration:
    """Pin the print() -> logger.info() migration for cycle-start/end events."""

    def test_no_print_calls_remain_in_module_source(self):
        """No raw print( calls may remain in agent_executor.py source.

        Every observable event in the module is expected to flow through the
        module-level logger. Raw print() calls bypass configured handlers.
        """
        import inspect
        import agent_executor

        source = inspect.getsource(agent_executor)
        assert "print(" not in source, (
            "agent_executor.py still contains print( — all observable events "
            "must use logger.info/debug/error to route through Python's "
            "logging infrastructure (file rotators, JSON serializers, log "
            "shippers)."
        )


@pytest.mark.asyncio
class TestAgentExecutorCycleLoggerBehavior:
    """Pin behavioral evidence that cycle-start/end emit INFO log records."""

    @patch("run_lifecycle.complete_run")
    @patch("phases.execution_phase.buy_shares")
    @patch("phases.decision_phase.DecisionMaker")
    @patch("phases.research_phase.MarketAnalyst")
    @patch("phases.decision_phase.Runner")
    @patch("guardrail_retry.Runner")
    @patch("run_lifecycle.update_phase")
    @patch("run_lifecycle.create_run")
    @patch("agent_executor.get_backend_client")
    @patch("agent_executor._get_account_report_raw")
    @patch("run_lifecycle.initialize_agent")
    @patch("run_lifecycle.broadcast_status")
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
        """execute_cycle must emit cycle-start (🤖) and cycle-end (✅) as INFO
        log records on the agent_executor logger — not via raw print()."""
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
            r for r in ae_records
            if r.levelno == logging.INFO
            and "🤖" in r.getMessage()
            and "starting portfolio review" in r.getMessage()
            and sample_agent_name in r.getMessage()
        ]
        end_records = [
            r for r in ae_records
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


# ============================================================================
# Test: Model pricing table + Usage type hint (Item #6 — live bug fix)
# ============================================================================
#
# These tests pin the contract that:
#   * `_extract_usage_metrics` no longer uses a hardcoded $0.15/$0.60 formula.
#   * A module-level `MODEL_PRICING` table drives cost calculation.
#   * Unknown models fall back to `cost_usd = None` with a WARNING log.
#   * The warning is deduplicated via `_UNKNOWN_MODELS_WARNED` so a noisy
#     unknown model name doesn't flood the log on every cycle.


class TestExtractUsageMetricsPricing:
    """Pin behaviour of the MODEL_PRICING lookup in extract_usage_metrics."""

    @pytest.fixture(autouse=True)
    def _reset_warned_set(self):
        """Clear the module-level dedupe set between tests for isolation."""
        import pricing
        pricing._UNKNOWN_MODELS_WARNED.clear()
        yield
        pricing._UNKNOWN_MODELS_WARNED.clear()

    @staticmethod
    def _make_usage_mock(input_tokens: int, output_tokens: int, model_name: str | None):
        """Build a Usage-shaped MagicMock matching the SDK's attribute surface.

        ``model_name=None`` simulates an SDK response with no request entries —
        callers will then fall back to the ``model_name`` argument passed to
        ``extract_usage_metrics``.
        """
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
        """gpt-4o-mini @ 1M input + 500k output must yield $0.15 + $0.30 = $0.45.

        Uses the table's published rate (0.15, 0.60) per 1M tokens to verify
        the formula and the lookup, not a single magic number.
        """
        from telemetry import extract_usage_metrics

        usage = self._make_usage_mock(
            input_tokens=1_000_000,
            output_tokens=500_000,
            model_name="gpt-4o-mini",
        )

        metrics = extract_usage_metrics(usage, model_name="ignored-fallback")

        # 1_000_000 * 0.15 / 1_000_000 = 0.15
        # 500_000   * 0.60 / 1_000_000 = 0.30
        # total = 0.45 — exact, no rounding artefacts at these magnitudes.
        assert metrics.costUsd == 0.45
        assert metrics.modelName == "gpt-4o-mini"

    def test_gpt_5_mini_uses_current_table_rates(self):
        """gpt-5-mini must compute cost from the table (not the legacy formula).

        At gpt-5-mini's $0.25/$2.00 rates, 1M input + 500k output is
        $0.25 + $1.00 = $1.25 — which is materially different from the
        legacy gpt-4o-mini hardcoded $0.15/$0.60 -> $0.45 computation.
        Asserting on $1.25 specifically catches the regression where the
        table is added but a call site still routes through the old formula.
        """
        from telemetry import extract_usage_metrics

        usage = self._make_usage_mock(
            input_tokens=1_000_000,
            output_tokens=500_000,
            model_name="gpt-5-mini",
        )

        metrics = extract_usage_metrics(usage, model_name="ignored-fallback")

        assert metrics.costUsd == 1.25
        assert metrics.modelName == "gpt-5-mini"

    def test_unknown_model_returns_none_and_logs_warning(self, caplog):
        """Unknown model → costUsd is None AND a WARNING log is emitted."""
        import logging
        from telemetry import extract_usage_metrics

        usage = self._make_usage_mock(
            input_tokens=100_000,
            output_tokens=50_000,
            model_name="some-future-unknown-model",
        )

        with caplog.at_level(logging.WARNING, logger="telemetry"):
            metrics = extract_usage_metrics(usage, model_name="ignored-fallback")

        assert metrics.costUsd is None
        assert metrics.modelName == "some-future-unknown-model"

        warning_records = [
            r for r in caplog.records
            if r.name == "telemetry"
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
        """Two calls with the same unknown model → exactly ONE warning log.

        The module-level _UNKNOWN_MODELS_WARNED set must suppress the second
        warning so a single misconfigured model doesn't flood the log on
        every trading cycle.
        """
        import logging
        from telemetry import extract_usage_metrics

        usage1 = self._make_usage_mock(
            input_tokens=100, output_tokens=50, model_name="dedupe-test-model"
        )
        usage2 = self._make_usage_mock(
            input_tokens=200, output_tokens=75, model_name="dedupe-test-model"
        )

        with caplog.at_level(logging.WARNING, logger="telemetry"):
            m1 = extract_usage_metrics(usage1, model_name="ignored")
            m2 = extract_usage_metrics(usage2, model_name="ignored")

        assert m1.costUsd is None
        assert m2.costUsd is None

        warning_records = [
            r for r in caplog.records
            if r.name == "telemetry"
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


# ============================================================================
# Test: _load_model_pricing — vendored LiteLLM JSON loader
# ============================================================================
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
    """Pin behaviour of _load_model_pricing() against the vendored JSON."""

    def test_load_model_pricing_returns_dict_with_known_openai_models(self):
        """Loader returns a dict containing gpt-4o-mini and gpt-5-mini with
        positive non-zero (input, output) per-1M tuples — guards against an
        empty/corrupt vendored file."""
        from pricing import _load_model_pricing

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
        """Loader must skip entries that don't have both `input_cost_per_token`
        and `output_cost_per_token` — covers LiteLLM's leading "sample_spec"
        placeholder plus any future malformed entries. Multiplies per-token
        values by 1_000_000 to match the per-1M convention."""
        from pricing import _load_model_pricing

        fake_json = {
            "sample_spec": {
                "max_tokens": 1024,
                "litellm_provider": "openai",
                # no cost fields → must be skipped
            },
            "missing-output-cost": {
                "input_cost_per_token": 0.0000002,
                # no output_cost_per_token → must be skipped
            },
            "model-with-extra-string-entry": "not-a-dict",  # must be skipped
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
        # The only valid entry survives and is converted per-token → per-1M.
        # pytest.approx for fp safety — 2e-07 * 1_000_000 binary-floats to
        # 0.19999999999999998, not exactly 0.2.
        assert "real-model" in pricing
        input_per_m, output_per_m = pricing["real-model"]
        assert input_per_m == pytest.approx(0.2)
        assert output_per_m == pytest.approx(0.8)


# ============================================================================
# Test: Prompt-Capture isinstance Narrowing (Item #5 — remove type: ignore)
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorPromptCaptureNarrowing:
    """Test the isinstance narrow at the two prompt-capture sites.

    Background: ``Agent.instructions`` is typed ``str | Callable[..., str] | None``
    by the SDK while ``RunContext.market_analyst_system_prompt`` and
    ``RunContext.decision_maker_system_prompt`` are ``str | None``. The
    capture sites at ``agent_executor.py`` lines 426 and 555 used to silence
    the resulting mypy ``[assignment]`` error with ``# type: ignore``; those
    suppressions have been replaced with an explicit ``isinstance`` narrow.

    These tests pin the runtime behaviour of that narrow:
      * When ``agent.instructions`` is a ``str``, the corresponding ctx field
        captures it verbatim.
      * When ``agent.instructions`` is a callable (e.g. a lambda dynamic
        prompt resolver), the ctx field is set to ``None`` AND a
        ``logger.debug`` message is emitted so the swap is visible in logs.
    """

    @patch("phases.research_phase.MarketAnalyst")
    @patch("guardrail_retry.Runner")
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
        """When agent.instructions is a str, ctx.market_analyst_system_prompt
        captures that exact string."""
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

        # No AgentExecutor instance needed — run_research_phase is a
        # module-level function (Task 6 of the decomposition plan).

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

        # The string flowed through unchanged.
        assert ctx.market_analyst_system_prompt == "you are a market analyst"

    @patch("phases.research_phase.MarketAnalyst")
    @patch("guardrail_retry.Runner")
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
        """When agent.instructions is a callable, ctx.market_analyst_system_prompt
        is None and a debug log is emitted on the agent_executor logger."""
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

        # No AgentExecutor instance needed — run_research_phase is a
        # module-level function (Task 6 of the decomposition plan).

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

        # The function object must not leak through to the context.
        assert ctx.market_analyst_system_prompt is None

        # A debug log entry must announce the callable-branch was taken.
        # After Task 6 of the decomposition plan the function was lifted out
        # of agent_executor.py into phases/research_phase.py — the logger
        # name follows that move.
        callable_debug_records = [
            r for r in caplog.records
            if r.name == "phases.research_phase"
            and r.levelno == logging.DEBUG
            and "market_analyst.agent.instructions is callable" in r.getMessage()
        ]
        assert callable_debug_records, (
            "Expected a DEBUG log on phases.research_phase announcing the "
            "callable branch was hit; got none. caplog records: "
            f"{[(r.name, r.levelname, r.getMessage()) for r in caplog.records]}"
        )

    @patch("phases.decision_phase.DecisionMaker")
    @patch("run_lifecycle.update_phase")
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
        """Same narrow at the Decision Maker site — callable → None + DEBUG log.

        Decision Maker is structurally identical to Market Analyst, so a single
        callable-branch test for it is enough to lock the symmetric behaviour
        (and to catch the case where only one of the two sites was migrated).
        """
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
                ctx=ctx, mcp_pool=mock_mcp_pool, force_trade=False,
                lifecycle=mock_lifecycle,
            )

        assert ctx.decision_maker_system_prompt is None

        callable_debug_records = [
            r for r in caplog.records
            if r.name == "phases.decision_phase"
            and r.levelno == logging.DEBUG
            and "decision_maker.agent.instructions is callable" in r.getMessage()
        ]
        assert callable_debug_records, (
            "Expected a DEBUG log on phases.decision_phase announcing the callable "
            "branch was hit at the Decision Maker site; got none. caplog records: "
            f"{[(r.name, r.levelname, r.getMessage()) for r in caplog.records]}"
        )


# ============================================================================
# Test: _extract_run_telemetry helper (Item #8 — DRY refactor)
# ============================================================================
#
# These tests pin the contract that a private ``_extract_run_telemetry`` method
# exists on ``AgentExecutor`` and consolidates the previously-duplicated
# 17-line tool-calls + usage-metrics + log-lines blocks that appeared in both
# ``_run_market_analyst`` and ``_run_decision_maker``. The helper accepts an
# SDK ``RunResult`` plus a model name and an agent label, and returns a
# ``(list[ToolCallDto], UsageMetrics)`` tuple. It must also emit the two
# observable INFO log lines so we don't silently regress observability when
# refactoring.


class TestAgentExecutorExtractRunTelemetry:
    """Pin behaviour of the extract_run_telemetry helper directly."""

    @pytest.fixture(autouse=True)
    def _reset_warned_set(self):
        """Clear the module-level dedupe set so unknown-model warnings don't
        leak across tests in this module."""
        import pricing
        pricing._UNKNOWN_MODELS_WARNED.clear()
        yield
        pricing._UNKNOWN_MODELS_WARNED.clear()

    @staticmethod
    def _make_run_result_mock(num_tool_calls: int):
        """Build a RunResult-shaped MagicMock.

        ``new_items`` is a list of opaque sentinels — the test patches
        ``extract_tool_calls`` so the helper's tool-call branch can be
        exercised independently of the SDK's item parsing.

        ``context_wrapper.usage`` carries the Usage-shaped attribute surface
        that ``extract_usage_metrics`` reads at runtime.
        """
        result = MagicMock()
        # new_items: opaque list passed through to extract_tool_calls (patched).
        result.new_items = [MagicMock() for _ in range(num_tool_calls)]
        # Usage shape — values chosen so costUsd is exactly computable from
        # the MODEL_PRICING entry for 'gpt-4o-mini' ($0.15 / $0.60 per 1M).
        result.context_wrapper.usage.total_tokens = 300
        result.context_wrapper.usage.input_tokens = 100
        result.context_wrapper.usage.output_tokens = 200
        result.context_wrapper.usage.requests = 1
        result.context_wrapper.usage.input_tokens_details = None
        result.context_wrapper.usage.output_tokens_details = None
        result.context_wrapper.usage.request_usage_entries = []
        return result

    @staticmethod
    def _make_parsed_call(name: str, params: dict, is_error: bool = False,
                          error_message: str | None = None):
        """Build a ParsedToolCall-shaped mock matching the fields the helper
        copies into ToolCallDto."""
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
        """The helper must return (list[ToolCallDto], UsageMetrics) with the
        right shapes, log both observability lines containing the agent label,
        and compute costUsd via the MODEL_PRICING table.
        """
        import logging
        from models.run_tracking import ToolCallDto
        from models.usage_metrics import UsageMetrics
        from telemetry import extract_run_telemetry

        # Build a result mock with 2 tool calls and a known usage shape.
        mock_result = self._make_run_result_mock(num_tool_calls=2)

        parsed_calls = [
            self._make_parsed_call("fetch_quote", {"symbol": "AAPL"}),
            self._make_parsed_call(
                "broken_tool", {"x": 1}, is_error=True, error_message="boom"
            ),
        ]

        # Patch extract_tool_calls so we control the parsed-call list directly.
        with patch(
            "telemetry.extract_tool_calls", return_value=parsed_calls
        ) as mock_extract:
            with caplog.at_level(logging.INFO, logger="telemetry"):
                tool_calls, usage_metrics = extract_run_telemetry(
                    mock_result,
                    model_name="gpt-4o-mini",
                    agent_label="Test Agent",
                )

        # extract_tool_calls must have been invoked on result.new_items.
        mock_extract.assert_called_once_with(mock_result.new_items)

        # Return tuple shape.
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
            r for r in caplog.records
            if r.name == "telemetry" and r.levelno == logging.INFO
        ]
        made_records = [
            r for r in ae_info
            if "Test Agent made" in r.getMessage()
            and "2 tool calls" in r.getMessage()
        ]
        usage_records = [
            r for r in ae_info
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


# ============================================================================
# Test: Completion message branches on execution_status (Minor #12)
# ============================================================================
#
# Before this fix, the PHASE_COMPLETED broadcast outcome message branched on
# `ctx.trade_id` truthiness. A FAILED BUY/SELL leaves trade_id=None, so it was
# incorrectly labeled "No trades (HOLD decision)" — the same message as a
# legitimate HOLD. After the restructure the message branches on
# `ctx.execution_result.execution_status` with three explicit cases
# (COMPLETED / SKIPPED / FAILED) plus a defensive fallback.


@pytest.mark.asyncio
class TestAgentExecutorCompletionMessageOnFailure:
    """Pin the FAILED-execution completion-message branch."""

    @patch("run_lifecycle.complete_run")
    @patch("phases.execution_phase.buy_shares")
    @patch("phases.decision_phase.DecisionMaker")
    @patch("phases.research_phase.MarketAnalyst")
    @patch("phases.decision_phase.Runner")
    @patch("guardrail_retry.Runner")
    @patch("run_lifecycle.update_phase")
    @patch("run_lifecycle.create_run")
    @patch("agent_executor.get_backend_client")
    @patch("agent_executor._get_account_report_raw")
    @patch("run_lifecycle.initialize_agent")
    @patch("run_lifecycle.broadcast_status")
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
        """A FAILED BUY/SELL must broadcast 'Completed - Trade attempted but failed'.

        Pre-fix bug: the PHASE_COMPLETED outcome_message branched on
        ``ctx.trade_id`` truthiness, so a FAILED BUY (trade_id=None) was
        mislabeled as 'Completed - No trades (HOLD decision)'.
        """
        from status_broadcaster import PHASE_COMPLETED
        from models.api_responses import AccountReport

        # ----- Standard happy-path setup, except buy_shares raises -----
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
            call_obj for call_obj in mock_broadcast.call_args_list
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


# ============================================================================
# Test: pricing.py module extraction (refactor Task 1)
# ============================================================================
#
# Pins the contract that the model-pricing block has been extracted from
# agent_executor.py into its own pricing module. agent_executor still
# re-exports MODEL_PRICING and _UNKNOWN_MODELS_WARNED for backwards
# compatibility within the package.


def test_pricing_module_exports_model_pricing():
    """Pricing constants live in their own module after Task 1 extraction."""
    from pricing import MODEL_PRICING, _UNKNOWN_MODELS_WARNED, _load_model_pricing

    assert isinstance(MODEL_PRICING, dict), (
        "MODEL_PRICING must be a dict mapping model name to pricing tuple"
    )
    assert "gpt-4o-mini" in MODEL_PRICING, (
        "MODEL_PRICING should include gpt-4o-mini as a known model"
    )
    assert isinstance(_UNKNOWN_MODELS_WARNED, set), (
        "_UNKNOWN_MODELS_WARNED must be a set for warning dedupe"
    )
    assert callable(_load_model_pricing), (
        "_load_model_pricing must be callable (loads pricing from JSON)"
    )


# ============================================================================
# Test: telemetry.py module extraction (refactor Task 2)
# ============================================================================
#
# Pins the contract that extract_usage_metrics (was _extract_usage_metrics)
# and extract_run_telemetry (was a method on AgentExecutor that didn't use
# self) live in a new telemetry module after Task 2 extraction.


def test_telemetry_module_exports_functions():
    """Telemetry helpers live in their own module after Task 2 extraction."""
    from telemetry import extract_usage_metrics, extract_run_telemetry

    assert callable(extract_usage_metrics), (
        "extract_usage_metrics must be callable (SDK Usage → UsageMetrics)"
    )
    assert callable(extract_run_telemetry), (
        "extract_run_telemetry must be callable (RunResult → tool calls + metrics)"
    )
