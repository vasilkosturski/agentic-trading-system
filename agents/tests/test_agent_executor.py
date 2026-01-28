"""Tests for AgentExecutor with explicit phase returns."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_executor import AgentExecutor
from models.orchestration import (
    CycleResult,
    RunContext,
    Phase1Result,
    Phase2Result,
    Phase3Result,
    Phase4Result,
    Phase5Result,
)
from models.llm_output import TradingDecision, ResearchResponse, ResearchSource
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
    return "Value Investor"

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
        candidates=["AAPL", "NVDA"],
        summary="Found 2 candidates",
        sources=[
            ResearchSource(title="Article 1", url="https://example.com/1"),
            ResearchSource(title="Article 2", url="https://example.com/2"),
        ],
    )

@pytest.fixture
def sample_decision():
    return TradingDecision(
        action="BUY",
        symbol="AAPL",
        quantity=100,
        rationale="Strong growth",
        fullReasoning="Detailed analysis",
        researchSources="[]",
        historicalContext="[]",
    )

@pytest.fixture
def mock_mcp_pool():
    return MagicMock()


# ============================================================================
# Test: Initialization
# ============================================================================

@pytest.mark.asyncio
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
# Test: Phase 1 - Start Run
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorPhase1StartRun:
    """Test Phase 1: Start run."""

    @patch("agent_executor.initialize_agent")
    @patch("agent_executor._get_balance_raw")
    @patch("agent_executor._get_holdings_raw")
    @patch("agent_executor.create_run")
    @patch("agent_executor.update_phase")
    @patch("agent_executor.broadcast_status")
    async def test_phase1_start_run_returns_phase1result(
        self,
        mock_broadcast,
        mock_update_phase,
        mock_create_run,
        mock_get_holdings,
        mock_get_balance,
        mock_initialize,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_balance,
        sample_holdings,
    ):
        """Test Phase 1 creates run and returns Phase1Result."""
        mock_initialize.return_value = None
        mock_get_balance.return_value = sample_balance
        mock_get_holdings.return_value = sample_holdings
        mock_create_run.return_value = 123
        mock_update_phase.return_value = True

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        result = await executor._phase1_start_run()

        # Verify Phase1Result returned
        assert isinstance(result, Phase1Result)
        assert result.run_id == 123
        assert result.research_start_time is not None

        # Verify API calls
        mock_initialize.assert_called_once_with(sample_agent_name)
        mock_create_run.assert_called_once_with(sample_agent_id)
        mock_update_phase.assert_called_once_with(123, RunPhase.RESEARCHING)

    @patch("agent_executor.initialize_agent")
    @patch("agent_executor.create_run")
    @patch("agent_executor.broadcast_status")
    async def test_phase1_start_run_fails_without_run_id(
        self,
        mock_broadcast,
        mock_create_run,
        mock_initialize,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
    ):
        """Test Phase 1 raises error if run creation fails."""
        mock_initialize.return_value = None
        mock_create_run.return_value = None

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        with pytest.raises(RuntimeError) as exc_info:
            await executor._phase1_start_run()

        assert "Failed to create run" in str(exc_info.value)


# ============================================================================
# Test: Phase 2 - Prepare Context
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorPhase2PrepareContext:
    """Test Phase 2: Prepare context."""

    @patch("agent_executor.get_recent_activity", new_callable=AsyncMock)
    async def test_phase2_prepare_context_returns_phase2result(
        self,
        mock_get_recent_activity,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_recent_activity,
    ):
        """Test Phase 2 returns Phase2Result with historical context."""
        # Mock async function to return typed model
        mock_get_recent_activity.return_value = sample_recent_activity

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        result = await executor._phase2_prepare_context(
            agent_id=sample_agent_id,
        )

        # Verify Phase2Result returned with typed model
        assert isinstance(result, Phase2Result)
        assert result.historical_context == sample_recent_activity
        assert result.historical_context.totalRuns == 1
        assert result.historical_context.totalTrades == 1

        mock_get_recent_activity.assert_called_once_with(sample_agent_id, days=30)


# ============================================================================
# Test: Phase 3 - Market Analyst
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorPhase3MarketAnalyst:
    """Test Phase 3: Market Analyst agent."""

    @patch("agent_executor.create_market_analyst_agent")
    @patch("agent_executor.Runner")
    @patch("agent_executor._get_balance_raw")
    @patch("agent_executor._get_holdings_raw")
    async def test_phase3_run_market_analyst_returns_phase3result(
        self,
        mock_get_holdings,
        mock_get_balance,
        mock_runner_class,
        mock_create_analyst,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_model_name,
        sample_research_response,
        sample_recent_activity,
        mock_mcp_pool,
    ):
        """Test Phase 3 returns Phase3Result with research results."""
        mock_get_balance.return_value = 100000.0
        mock_get_holdings.return_value = []

        mock_analyst = MagicMock()
        mock_create_analyst.return_value = mock_analyst

        mock_result = MagicMock()
        mock_result.output = sample_research_response
        mock_runner_class.run = AsyncMock(return_value=mock_result)

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name
        )

        result = await executor._phase3_run_market_analyst(
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name=sample_model_name,
            historical_context=sample_recent_activity,
            mcp_pool=mock_mcp_pool,
            tracker=MagicMock(),
        )

        # Verify Phase3Result returned
        assert isinstance(result, Phase3Result)
        assert result.research_response == sample_research_response
        assert len(result.candidates) == 2
        assert result.notes == sample_research_response.summary

        mock_create_analyst.assert_called_once()
        mock_runner_class.run.assert_called_once()


# ============================================================================
# Test: Phase 4 - Decision Maker
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorPhase4DecisionMaker:
    """Test Phase 4: Decision Maker agent."""

    @patch("agent_executor.create_decision_maker_agent")
    @patch("agent_executor.Runner")
    @patch("agent_executor.update_phase")
    @patch("agent_executor.broadcast_status")
    @patch("agent_executor._get_balance_raw")
    @patch("agent_executor._get_holdings_raw")
    async def test_phase4_run_decision_maker_returns_phase4result(
        self,
        mock_get_holdings,
        mock_get_balance,
        mock_broadcast,
        mock_update_phase,
        mock_runner_class,
        mock_create_decision_maker,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_model_name,
        sample_research_response,
        sample_recent_activity,
        mock_mcp_pool,
        sample_decision,
    ):
        """Test Phase 4 returns Phase4Result with decision."""
        mock_get_balance.return_value = 100000.0
        mock_get_holdings.return_value = []
        mock_update_phase.return_value = True

        mock_decision_maker = MagicMock()
        mock_create_decision_maker.return_value = mock_decision_maker

        mock_result = MagicMock()
        mock_runner_class.run = AsyncMock(return_value=mock_result)

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name
        )
        # Pre-set pending decision (simulating decide_action tool)
        executor._pending_decision = sample_decision

        result = await executor._phase4_run_decision_maker(
            run_id=123,
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            model_name=sample_model_name,
            research_response=sample_research_response,
            historical_context=sample_recent_activity,
            mcp_pool=mock_mcp_pool,
            force_trade=False,
            tracker=MagicMock(),
        )

        # Verify Phase4Result returned
        assert isinstance(result, Phase4Result)
        assert result.decision == sample_decision
        assert result.decision_start_time is not None

        mock_update_phase.assert_called_once_with(123, RunPhase.DECIDING)


# ============================================================================
# Test: Phase 5 - Execute Decision
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorPhase5ExecuteDecision:
    """Test Phase 5: Execute decision."""

    async def test_phase5_raises_error_when_no_decision(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
    ):
        """Test Phase 5 raises error when no decision provided."""
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        with pytest.raises(RuntimeError) as exc_info:
            await executor._phase5_execute_decision(
                run_id=123,
                agent_id=sample_agent_id,
                decision=None,
            )

        assert "no decision was recorded" in str(exc_info.value)

    @patch("agent_executor.buy_shares")
    @patch("agent_executor.update_phase")
    @patch("agent_executor.broadcast_status")
    async def test_phase5_execute_buy_decision(
        self,
        mock_broadcast,
        mock_update_phase,
        mock_buy,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_decision,
    ):
        """Test Phase 5 executes BUY decision."""
        mock_update_phase.return_value = True
        mock_buy.return_value = MagicMock(tradeId=456)

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        result = await executor._phase5_execute_decision(
            run_id=123,
            agent_id=sample_agent_id,
            decision=sample_decision,
        )

        # Verify Phase5Result returned
        assert isinstance(result, Phase5Result)
        assert result.trade_id == 456
        assert result.trade_count == 1
        assert result.execution_status == PhaseStatus.COMPLETED

        mock_update_phase.assert_called_once_with(123, RunPhase.TRADING)
        mock_buy.assert_called_once()

    async def test_phase5_execute_hold_decision(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
    ):
        """Test Phase 5 handles HOLD decision."""
        hold_decision = TradingDecision(
            action="HOLD",
            symbol="",
            quantity=0,
            rationale="No good opportunities",
            fullReasoning="Detailed analysis",
            researchSources="[]",
            historicalContext="[]",
        )

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        result = await executor._phase5_execute_decision(
            run_id=123,
            agent_id=sample_agent_id,
            decision=hold_decision,
        )

        # Verify Phase5Result returned
        assert isinstance(result, Phase5Result)
        assert result.trade_id is None
        assert result.trade_count == 0
        assert result.execution_status == PhaseStatus.SKIPPED


# ============================================================================
# Test: Phase 6 - Finalize
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorPhase6Finalize:
    """Test Phase 6: Finalize cycle."""

    @patch("agent_executor.complete_run")
    @patch("agent_executor.broadcast_status")
    async def test_phase6_finalize_with_trade(
        self,
        mock_broadcast,
        mock_complete_run,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_decision,
    ):
        """Test Phase 6 completes run with trade data."""
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
            trade_id=456,
            trade_count=1,
            execution_status=PhaseStatus.COMPLETED,
        )

        await executor._phase6_finalize(ctx)

        mock_complete_run.assert_called_once()
        call_args = mock_complete_run.call_args
        assert call_args[0][0] == 123  # run_id


# ============================================================================
# Test: Error Handling
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorErrorHandling:
    """Test error handling."""

    @patch("agent_executor.update_phase")
    async def test_handle_cycle_error_with_context(
        self,
        mock_update_phase,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
    ):
        """Test error handler updates phase to ERROR."""
        mock_update_phase.return_value = True

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

        mock_update_phase.assert_called_once_with(123, RunPhase.ERROR)

    @patch("agent_executor.update_phase")
    async def test_handle_cycle_error_without_context(
        self,
        mock_update_phase,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
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
    @patch("agent_executor.create_decision_maker_agent")
    @patch("agent_executor.create_market_analyst_agent")
    @patch("agent_executor.Runner")
    @patch("agent_executor.update_phase")
    @patch("agent_executor.create_run")
    @patch("agent_executor.get_recent_activity", new_callable=AsyncMock)
    @patch("agent_executor._get_balance_raw")
    @patch("agent_executor._get_holdings_raw")
    @patch("agent_executor.initialize_agent")
    @patch("agent_executor.broadcast_status")
    @patch("agent_executor.ToolTracker")
    async def test_execute_cycle_success_with_buy(
        self,
        mock_tracker_class,
        mock_broadcast,
        mock_initialize,
        mock_get_holdings,
        mock_get_balance,
        mock_get_recent_activity,
        mock_create_run,
        mock_update_phase,
        mock_runner_class,
        mock_create_analyst,
        mock_create_decision_maker,
        mock_buy,
        mock_complete_run,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_model_name,
        sample_research_response,
        sample_recent_activity,
        sample_decision,
        mock_mcp_pool,
    ):
        """Test full cycle with successful BUY decision."""
        # Setup mocks
        mock_initialize.return_value = None
        mock_get_balance.return_value = 100000.0
        mock_get_holdings.return_value = []
        mock_get_recent_activity.return_value = sample_recent_activity
        mock_create_run.return_value = 123
        mock_update_phase.return_value = True
        mock_complete_run.return_value = True

        mock_tracker_instance = MagicMock()
        mock_tracker_class.return_value = mock_tracker_instance

        # Phase 3: Research
        mock_analyst = MagicMock()
        mock_create_analyst.return_value = mock_analyst
        mock_research_result = MagicMock()
        mock_research_result.output = sample_research_response

        # Phase 4: Decision
        mock_decision_maker = MagicMock()
        mock_create_decision_maker.return_value = mock_decision_maker
        mock_decision_result = MagicMock()

        mock_runner_class.run = AsyncMock(side_effect=[mock_research_result, mock_decision_result])

        # Phase 5: Trade
        mock_buy.return_value = MagicMock(tradeId=456)

        # Create executor
        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_model_name
        )
        executor._pending_decision = sample_decision

        # Execute cycle
        result = await executor.execute_cycle(mcp_pool=mock_mcp_pool, force_trade=False)

        # Verify result
        assert isinstance(result, CycleResult)
        assert result.decision == sample_decision
        assert result.trade_count == 1
        assert result.run_id == 123


# ============================================================================
# Test: Helper Methods
# ============================================================================

@pytest.mark.asyncio
class TestAgentExecutorHelperMethods:
    """Test helper methods."""

    def test_store_decision(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
    ):
        """Test store_decision creates TradingDecision."""
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style)

        executor.store_decision(
            action="BUY",
            symbol="AAPL",
            quantity=100,
            rationale="Strong growth",
            full_reasoning="Detailed analysis",
            research_sources="[]",
            historical_context="[]",
        )

        assert executor._pending_decision is not None
        assert executor._pending_decision.action == "BUY"
        assert executor._pending_decision.symbol == "AAPL"
        assert executor._pending_decision.quantity == 100
