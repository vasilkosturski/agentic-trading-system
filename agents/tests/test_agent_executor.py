"""Comprehensive tests for AgentExecutor class.

Tests follow the pattern from grounding research:
- Mock tool execution functions (not the LLM)
- Use aioresponses for HTTP mocking
- Test behavior, not implementation details

Updated for RunContext-based architecture:
- RunContext passed through all phases (explicit data flow)
- No instance variables for per-run state
- Fail-fast error handling
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_executor import AgentExecutor
from models import TradeResult, CycleResult
from models.orchestration import RunContext, SharedPhaseContext
from models.run_tracking import PhaseStatus, SourceDto


@pytest.mark.asyncio
class TestAgentExecutorInitialization:
    """Test AgentExecutor initialization."""

    def test_init(self, sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy, sample_model_name):
        """Test AgentExecutor initialization sets up agent identity."""
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy, sample_model_name)

        assert executor.agent_id == sample_agent_id
        assert executor.name == sample_agent_name
        assert executor.agent_style == sample_agent_style
        assert executor.strategy == sample_strategy
        assert executor.model_name == sample_model_name
        # No per-run state in new architecture
        assert executor._pending_decision is None


@pytest.mark.asyncio
class TestAgentExecutorPhase1StartRun:
    """Test Phase 1: Initialize cycle and return RunContext."""

    @patch("agent_executor.initialize_agent")
    @patch("agent_executor._get_balance_raw")
    @patch("agent_executor._get_holdings_raw")
    @patch("agent_executor.create_run")
    @patch("agent_executor.update_phase")
    @patch("agent_executor.broadcast_status")
    @patch("agent_executor.ToolTracker")
    async def test_phase1_start_run_returns_context(
        self,
        mock_tracker_class,
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
        """Test Phase 1 creates run and returns RunContext."""
        # Setup mocks
        mock_initialize.return_value = None
        mock_get_balance.return_value = sample_balance
        mock_get_holdings.return_value = sample_holdings
        mock_create_run.return_value = 123
        mock_update_phase.return_value = True
        mock_tracker_instance = MagicMock()
        mock_tracker_class.return_value = mock_tracker_instance

        # Create executor
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)

        # Execute Phase 1
        ctx = await executor._phase1_start_run()

        # Verify RunContext returned with correct values
        assert isinstance(ctx, RunContext)
        assert ctx.run_id == 123
        assert ctx.agent_id == sample_agent_id
        assert ctx.agent_name == sample_agent_name
        assert ctx.agent_style == sample_agent_style
        assert ctx.strategy == sample_strategy
        assert ctx.research_start_time is not None
        assert ctx.tracker is not None

        # Verify API calls
        mock_initialize.assert_called_once_with(sample_agent_name)
        mock_create_run.assert_called_once_with(sample_agent_id)
        mock_update_phase.assert_called_once_with(123, "RESEARCHING")

        # Verify research sources added
        assert len(ctx.research_sources) >= 1
        assert ctx.research_sources[0].type == "system_context"

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

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)

        with pytest.raises(RuntimeError) as exc_info:
            await executor._phase1_start_run()

        assert "Failed to create run" in str(exc_info.value)


@pytest.mark.asyncio
class TestAgentExecutorPhase2PrepareContext:
    """Test Phase 2: Prepare context."""

    @patch("agent_executor.get_recent_activity")
    async def test_phase2_prepare_context_updates_ctx(
        self,
        mock_get_recent_activity,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_recent_activity,
    ):
        """Test Phase 2 updates RunContext with SharedPhaseContext."""
        mock_get_recent_activity.return_value = sample_recent_activity

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)
        
        # Create RunContext
        ctx = RunContext(
            run_id=123,
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            strategy=sample_strategy,
            model_name="gpt-4o-mini",
            research_start_time=datetime.now(),
        )

        # Execute Phase 2
        await executor._phase2_prepare_context(ctx)

        # Verify SharedPhaseContext set
        assert ctx.shared_context is not None
        assert isinstance(ctx.shared_context, SharedPhaseContext)
        assert ctx.shared_context.historical_context == sample_recent_activity

        # Verify research source added
        assert len(ctx.research_sources) >= 1

        mock_get_recent_activity.assert_called_once_with(sample_agent_name, days=30)


@pytest.mark.asyncio
class TestAgentExecutorPhase3MarketAnalyst:
    """Test Phase 3: Market Analyst agent."""

    @patch("agent_executor.create_market_analyst_agent")
    @patch("agent_executor.Runner")
    @patch("agent_executor._get_balance_raw")
    @patch("agent_executor._get_holdings_raw")
    async def test_phase3_run_market_analyst_updates_ctx(
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
        mock_mcp_pool,
    ):
        """Test Phase 3 updates RunContext with research results."""
        mock_get_balance.return_value = 100000.0
        mock_get_holdings.return_value = []

        mock_analyst = MagicMock()
        mock_create_analyst.return_value = mock_analyst

        mock_result = MagicMock()
        mock_result.output = sample_research_response
        mock_runner_class.run = AsyncMock(return_value=mock_result)

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy, sample_model_name
        )

        # Create RunContext with shared_context
        ctx = RunContext(
            run_id=123,
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            strategy=sample_strategy,
            model_name=sample_model_name,
            research_start_time=datetime.now(),
            tracker=MagicMock(),
        )
        ctx.shared_context = SharedPhaseContext(historical_context="{}")

        # Execute Phase 3
        await executor._phase3_run_market_analyst(ctx, mock_mcp_pool)

        # Verify RunContext updated
        assert ctx.research_response == sample_research_response
        assert len(ctx.research_candidates) > 0
        assert ctx.research_notes == sample_research_response.summary

        # Verify Market Analyst created
        mock_create_analyst.assert_called_once()
        mock_runner_class.run.assert_called_once()


@pytest.mark.asyncio
class TestAgentExecutorPhase4DecisionMaker:
    """Test Phase 4: Decision Maker agent."""

    @patch("agent_executor.create_decision_maker_agent")
    @patch("agent_executor.Runner")
    @patch("agent_executor.update_phase")
    @patch("agent_executor._get_balance_raw")
    @patch("agent_executor._get_holdings_raw")
    async def test_phase4_run_decision_maker_updates_ctx(
        self,
        mock_get_holdings,
        mock_get_balance,
        mock_update_phase,
        mock_runner_class,
        mock_create_decision_maker,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_model_name,
        sample_research_response,
        mock_mcp_pool,
        sample_decision,
    ):
        """Test Phase 4 updates RunContext with decision."""
        mock_get_balance.return_value = 100000.0
        mock_get_holdings.return_value = []
        mock_update_phase.return_value = True

        mock_decision_maker = MagicMock()
        mock_create_decision_maker.return_value = mock_decision_maker

        mock_result = MagicMock()
        mock_runner_class.run = AsyncMock(return_value=mock_result)

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy, sample_model_name
        )
        # Pre-set pending decision (simulating decide_action tool)
        executor._pending_decision = sample_decision

        # Create RunContext
        ctx = RunContext(
            run_id=123,
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            strategy=sample_strategy,
            model_name=sample_model_name,
            research_start_time=datetime.now(),
            tracker=MagicMock(),
        )
        ctx.shared_context = SharedPhaseContext(historical_context="{}")
        ctx.research_response = sample_research_response

        # Execute Phase 4
        await executor._phase4_run_decision_maker(ctx, mock_mcp_pool, force_trade=False)

        # Verify RunContext updated
        assert ctx.decision == sample_decision
        assert ctx.decision_start_time is not None

        mock_update_phase.assert_called_once_with(123, "DECIDING")


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
        """Test Phase 5 raises error when no decision in context."""
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)

        ctx = RunContext(
            run_id=123,
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            strategy=sample_strategy,
            model_name="gpt-4o-mini",
            research_start_time=datetime.now(),
        )
        ctx.decision = None

        with pytest.raises(RuntimeError) as exc_info:
            await executor._phase5_execute_decision(ctx)

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
        """Test Phase 5 executes BUY decision and updates context."""
        mock_buy.return_value = TradeResult(
            tradeId=101, symbol="NVDA", quantity=50, price=142.50, newBalance=92875.00
        )
        mock_update_phase.return_value = True

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)

        ctx = RunContext(
            run_id=123,
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            strategy=sample_strategy,
            model_name="gpt-4o-mini",
            research_start_time=datetime.now(),
            tracker=MagicMock(),
        )
        ctx.decision = sample_decision

        await executor._phase5_execute_decision(ctx)

        # Verify context updated
        assert ctx.trade_count == 1
        assert ctx.trade_id == 101
        assert ctx.execution_status == PhaseStatus.COMPLETED

        mock_update_phase.assert_called_once_with(123, "TRADING")
        mock_buy.assert_called_once()

    @patch("agent_executor.broadcast_status")
    async def test_phase5_execute_hold_decision(
        self, mock_broadcast, sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy
    ):
        """Test Phase 5 handles HOLD decision."""
        from models import TradingDecision
        hold_decision = TradingDecision(
            action="HOLD",
            symbol="",
            quantity=0,
            rationale="Portfolio looks good",
            fullReasoning="No changes needed.",
            researchSources="[]",
            historicalContext="[]",
        )

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)

        ctx = RunContext(
            run_id=123,
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            strategy=sample_strategy,
            model_name="gpt-4o-mini",
            research_start_time=datetime.now(),
            tracker=MagicMock(),
        )
        ctx.decision = hold_decision

        await executor._phase5_execute_decision(ctx)

        assert ctx.trade_count == 0
        assert ctx.execution_status == PhaseStatus.SKIPPED


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
        """Test Phase 6 finalizes cycle with trade."""
        mock_complete_run.return_value = True

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)

        ctx = RunContext(
            run_id=123,
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            strategy=sample_strategy,
            model_name="gpt-4o-mini",
            research_start_time=datetime.now(),
        )
        ctx.decision_start_time = datetime.now()
        ctx.decision = sample_decision
        ctx.trade_count = 1
        ctx.execution_status = PhaseStatus.COMPLETED

        await executor._phase6_finalize(ctx)

        mock_complete_run.assert_called_once()
        call_args = mock_complete_run.call_args
        assert call_args[0][0] == 123
        complete_data = call_args[0][1]
        assert complete_data.decision.value == "BUY"


@pytest.mark.asyncio
class TestAgentExecutorErrorHandling:
    """Test error handling."""

    @patch("agent_executor.update_phase")
    @patch("agent_executor.complete_run")
    @patch("agent_executor.broadcast_status")
    async def test_handle_cycle_error_with_context(
        self,
        mock_broadcast,
        mock_complete_run,
        mock_update_phase,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
    ):
        """Test error handling with RunContext."""
        mock_update_phase.return_value = True
        mock_complete_run.return_value = True

        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)

        ctx = RunContext(
            run_id=123,
            agent_id=sample_agent_id,
            agent_name=sample_agent_name,
            agent_style=sample_agent_style,
            strategy=sample_strategy,
            model_name="gpt-4o-mini",
            research_start_time=datetime.now(),
        )

        error = Exception("Test error")
        await executor._handle_cycle_error(error, ctx)

        mock_update_phase.assert_called_once_with(123, "ERROR")
        mock_complete_run.assert_called_once()

    @patch("agent_executor.broadcast_status")
    async def test_handle_cycle_error_without_context(
        self,
        mock_broadcast,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
    ):
        """Test error handling when context is None (Phase 1 failed)."""
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)

        error = Exception("Phase 1 failed")
        await executor._handle_cycle_error(error, None)

        # Should still broadcast error
        mock_broadcast.assert_called_once()


@pytest.mark.asyncio
class TestAgentExecutorFullCycle:
    """Test full execution cycle integration."""

    @patch("agent_executor.initialize_agent")
    @patch("agent_executor._get_balance_raw")
    @patch("agent_executor._get_holdings_raw")
    @patch("agent_executor.create_run")
    @patch("agent_executor.update_phase")
    @patch("agent_executor.complete_run")
    @patch("agent_executor.get_recent_activity")
    @patch("agent_executor.buy_shares")
    @patch("agent_executor.broadcast_status")
    @patch("agent_executor.ToolTracker")
    async def test_execute_cycle_success_with_buy(
        self,
        mock_tracker_class,
        mock_broadcast,
        mock_buy,
        mock_get_recent_activity,
        mock_complete_run,
        mock_update_phase,
        mock_create_run,
        mock_get_holdings,
        mock_get_balance,
        mock_initialize,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_model_name,
        sample_balance,
        sample_holdings,
        sample_recent_activity,
        sample_decision,
        sample_research_response,
        mock_mcp_pool,
        mocker,
    ):
        """Test full execution cycle with BUY decision."""
        mock_initialize.return_value = None
        mock_get_balance.return_value = sample_balance
        mock_get_holdings.return_value = sample_holdings
        mock_create_run.return_value = 123
        mock_update_phase.return_value = True
        mock_complete_run.return_value = True
        mock_get_recent_activity.return_value = sample_recent_activity
        mock_buy.return_value = TradeResult(
            tradeId=103, symbol="NVDA", quantity=50, price=142.50, newBalance=92875.00
        )

        mock_tracker_instance = MagicMock()
        mock_tracker_class.return_value = mock_tracker_instance

        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy, sample_model_name
        )

        # Mock Phase 3 to update context
        async def mock_phase3(ctx, mcp_pool):
            ctx.research_response = sample_research_response
            ctx.research_candidates = sample_research_response.candidates
            ctx.research_notes = sample_research_response.summary

        mocker.patch.object(executor, "_phase3_run_market_analyst", side_effect=mock_phase3)

        # Mock Phase 4 to set decision
        async def mock_phase4(ctx, mcp_pool, force_trade):
            executor._pending_decision = sample_decision
            ctx.decision = sample_decision
            ctx.decision_start_time = datetime.now()

        mocker.patch.object(executor, "_phase4_run_decision_maker", side_effect=mock_phase4)

        # Execute full cycle
        result = await executor.execute_cycle(mcp_pool=mock_mcp_pool, force_trade=False)

        # Verify result
        assert isinstance(result, CycleResult)
        assert result.decision.action == "BUY"
        assert result.trade_count == 1
        assert result.run_id == 123

        # Verify cleanup (pending decision cleared)
        assert executor._pending_decision is None


@pytest.mark.asyncio
class TestAgentExecutorHelperMethods:
    """Test helper methods."""

    def test_store_decision(
        self, sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy
    ):
        """Test decision storage in _pending_decision."""
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)

        executor.store_decision(
            action="BUY",
            symbol="AAPL",
            quantity=100,
            rationale="Strong fundamentals",
            full_reasoning="Complete analysis here",
            research_sources='{"summary": "test"}',
            historical_context='{"summary": "test"}',
        )

        assert executor._pending_decision is not None
        assert executor._pending_decision.action == "BUY"
        assert executor._pending_decision.symbol == "AAPL"
        assert executor._pending_decision.quantity == 100
