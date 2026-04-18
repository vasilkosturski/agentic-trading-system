"""Tests for AgentExecutor with explicit phase returns."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_executor import AgentExecutor
from models.investment_style import InvestmentStyle
from models.orchestration import (
    CycleResult,
    RunContext,
    AccountData,
    ResearchResult,
    DecisionResult,
    ExecutionResult,
)
from models.llm_output import CandidateStock, TradingDecision, ResearchResponse, WebSource
from models.run_tracking import PhaseStatus, RunPhase, TradeDecision


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
# Test: Start Run
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorStartRun:
    """Test _start_run method."""

    @patch("agent_executor.initialize_agent")
    @patch("agent_executor.create_run")
    @patch("agent_executor.update_phase")
    @patch("agent_executor.broadcast_status")
    async def test_start_run_returns_run_id(
        self,
        mock_broadcast,
        mock_update_phase,
        mock_create_run,
        mock_initialize,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
    ):
        """Test _start_run creates run and returns run_id."""
        mock_initialize.return_value = None
        mock_create_run.return_value = 123
        mock_update_phase.return_value = True

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        result = await executor._start_run()

        # Verify run_id returned
        assert isinstance(result, int)
        assert result == 123

        # Verify API calls
        mock_initialize.assert_called_once_with(sample_agent_name)
        mock_create_run.assert_called_once_with(sample_agent_id)
        mock_update_phase.assert_called_once_with(123, RunPhase.RESEARCHING)


# ============================================================================
# Test: Fetch Account Data & Recent Activity
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

    @patch("agent_executor.get_backend_client")
    async def test_fetch_recent_activity_returns_response(
        self,
        mock_get_backend_client,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_recent_activity,
    ):
        """Test _fetch_recent_activity returns RecentActivityResponse."""
        mock_client = AsyncMock()
        mock_client.get_recent_activity.return_value = sample_recent_activity
        mock_get_backend_client.return_value = mock_client

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        result = await executor._fetch_recent_activity(sample_agent_id)

        from models.api_responses import RecentActivityResponse
        assert isinstance(result, RecentActivityResponse)
        assert result.totalRuns == 1
        assert result.totalTrades == 1

        mock_client.get_recent_activity.assert_called_once_with(sample_agent_id, days=30)


# ============================================================================
# Test: Market Analyst
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorMarketAnalyst:
    """Test _run_market_analyst method."""

    @patch("agent_executor.MarketAnalyst")
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
        # Setup mock MarketAnalyst
        mock_analyst_instance = MagicMock()
        mock_analyst_instance.agent = MagicMock()
        mock_analyst_instance.build_prompt.return_value = "test prompt"
        mock_market_analyst_class.create = AsyncMock(return_value=mock_analyst_instance)

        # Setup mock Runner result with proper usage metrics
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

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name
        )

        # Create minimal context with tracker
        mock_tracker = MagicMock()
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
            tracker=mock_tracker,
        )

        result = await executor._run_market_analyst(ctx, mock_mcp_pool)

        # Verify ResearchResult returned
        assert isinstance(result, ResearchResult)
        assert result.research_response == sample_research_response
        # Candidates extracted as symbol strings from CandidateStock objects
        assert len(result.candidates) == 2
        assert result.candidates == ["AAPL", "NVDA"]
        assert result.notes == sample_research_response.summary


# ============================================================================
# Test: Decision Maker
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorDecisionMaker:
    """Test _run_decision_maker method."""

    @patch("agent_executor.DecisionMaker")
    @patch("agent_executor.Runner")
    @patch("agent_executor.update_phase")
    @patch("agent_executor.broadcast_status")
    async def test_run_decision_maker_returns_decision_result(
        self,
        mock_broadcast,
        mock_update_phase,
        mock_runner_class,
        mock_decision_maker_class,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_model_name,
        sample_research_response,
        sample_recent_activity,
        mock_mcp_pool,
        sample_decision,
    ):
        """Test _run_decision_maker returns DecisionResult."""
        mock_update_phase.return_value = True

        # Setup mock DecisionMaker
        mock_dm_instance = MagicMock()
        mock_dm_instance.agent = MagicMock()
        mock_dm_instance.build_prompt.return_value = "test prompt"
        mock_decision_maker_class.create = AsyncMock(return_value=mock_dm_instance)

        # Setup mock Runner result with proper usage metrics
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

        mock_dm_instance.model_name = "gpt-4o"

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name
        )

        # Create context with research response
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
            research_response=sample_research_response,
        )

        result = await executor._run_decision_maker(ctx, mock_mcp_pool, force_trade=False)

        # Verify DecisionResult returned
        assert isinstance(result, DecisionResult)
        assert result.decision == sample_decision
        assert result.decision_start_time is not None

        mock_update_phase.assert_called_once_with(123, RunPhase.DECIDING)


# ============================================================================
# Test: Execute Trade
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorExecuteTrade:
    """Test _execute_trade method."""

    async def test_execute_trade_raises_error_when_no_decision(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
    ):
        """Test _execute_trade raises error when no decision provided."""
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        with pytest.raises(RuntimeError) as exc_info:
            await executor._execute_trade(
                run_id=123,
                agent_id=sample_agent_id,
                decision=None,
            )

        assert "no decision was recorded" in str(exc_info.value)

    @patch("agent_executor.buy_shares")
    @patch("agent_executor.update_phase")
    @patch("agent_executor.broadcast_status")
    async def test_execute_trade_buy_decision(
        self,
        mock_broadcast,
        mock_update_phase,
        mock_buy,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_decision,
    ):
        """Test _execute_trade executes BUY decision."""
        mock_update_phase.return_value = True
        mock_buy.return_value = MagicMock(tradeId=456)

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        result = await executor._execute_trade(
            run_id=123,
            agent_id=sample_agent_id,
            decision=sample_decision,
        )

        # Verify ExecutionResult returned
        assert isinstance(result, ExecutionResult)
        assert result.trade_id == 456
        assert result.execution_status == PhaseStatus.COMPLETED

        mock_update_phase.assert_called_once_with(123, RunPhase.TRADING)
        mock_buy.assert_called_once()

    async def test_execute_trade_hold_decision(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
    ):
        """Test _execute_trade handles HOLD decision."""
        hold_decision = TradingDecision(
            action="HOLD",
            symbol="",
            quantity=0,
            rationale="No good opportunities",
            portfolioContext="Portfolio is well-positioned, no need to add exposure.",
            historicalContext="Recent trades have been mixed, caution warranted.",
            researchContext="Analysis shows no compelling opportunities at this time.",
        )

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        result = await executor._execute_trade(
            run_id=123,
            agent_id=sample_agent_id,
            decision=hold_decision,
        )

        # Verify ExecutionResult returned
        assert isinstance(result, ExecutionResult)
        assert result.trade_id is None
        assert result.execution_status == PhaseStatus.SKIPPED


# ============================================================================
# Test: Finalize Run
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorFinalizeRun:
    """Test _finalize_run method."""

    @patch("agent_executor.complete_run")
    @patch("agent_executor.broadcast_status")
    async def test_finalize_run_with_trade(
        self,
        mock_broadcast,
        mock_complete_run,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_decision,
        sample_research_response,
    ):
        """Test _finalize_run completes run with trade data."""
        mock_complete_run.return_value = True

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        ctx = RunContext(
            run_id=123,
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name="gpt-4o-mini",
            research_start_time=datetime.now(),
            decision_start_time=datetime.now(),
            decision=sample_decision,
            research_response=sample_research_response,
            trade_id=456,
            execution_status=PhaseStatus.COMPLETED,
        )

        await executor._finalize_run(ctx)

        mock_complete_run.assert_called_once()
        call_args = mock_complete_run.call_args
        assert call_args[0][0] == 123  # run_id

        # Verify rationale flows through to CompleteRunData
        complete_data = call_args[0][1]
        assert complete_data.decision.reasoning is not None
        assert complete_data.decision.reasoning.rationale == "Strong growth"


# ============================================================================
# Test: Error Handling
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorErrorHandling:
    """Test error handling."""

    @patch("agent_executor.complete_run")
    @patch("agent_executor.update_phase")
    @patch("agent_executor.broadcast_status")
    async def test_handle_cycle_error_with_context(
        self,
        mock_broadcast,
        mock_update_phase,
        mock_complete_run,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
    ):
        """Test error handler updates phase to ERROR."""
        mock_update_phase.return_value = True
        mock_complete_run.return_value = True

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        ctx = RunContext(
            run_id=123,
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name="gpt-4o-mini",
            research_start_time=datetime.now(),
        )

        await executor._handle_cycle_error(Exception("Test error"), ctx)

        # Error handler should set phase to ERROR (not call complete_run)
        mock_update_phase.assert_called_once()
        mock_complete_run.assert_not_called()

    @patch("agent_executor.update_phase")
    async def test_handle_cycle_error_without_context(
        self,
        mock_update_phase,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
    ):
        """Test error handler handles missing context gracefully."""
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        # Should not raise
        await executor._handle_cycle_error(Exception("Test error"), None)

        mock_update_phase.assert_not_called()


# ============================================================================
# Test: Full Cycle
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorFullCycle:
    """Test full execute_cycle."""

    @patch("agent_executor.complete_run")
    @patch("agent_executor.buy_shares")
    @patch("agent_executor.DecisionMaker")
    @patch("agent_executor.MarketAnalyst")
    @patch("agent_executor.Runner")
    @patch("guardrail_retry.Runner")
    @patch("agent_executor.update_phase")
    @patch("agent_executor.create_run")
    @patch("agent_executor.get_backend_client")
    @patch("agent_executor._get_account_report_raw")
    @patch("agent_executor.initialize_agent")
    @patch("agent_executor.broadcast_status")
    @patch("agent_executor.ToolTracker")
    async def test_execute_cycle_success_with_buy(
        self,
        mock_tracker_class,
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

        mock_tracker_instance = MagicMock()
        mock_tracker_class.return_value = mock_tracker_instance

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

        # Decision Maker runs through agent_executor.Runner
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


