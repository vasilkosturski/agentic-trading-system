"""Comprehensive tests for AgentExecutor class.

Tests follow the pattern from grounding research:
- Mock tool execution functions (not the LLM)
- Use aioresponses for HTTP mocking
- Test behavior, not implementation details

Updated for new phase-based Trading Runs API:
- create_run() replaces start_run()
- update_phase() for phase transitions
- complete_run() replaces end_run()
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch, call, create_autospec

import pytest

from agent_executor import AgentExecutor
from agents.items import ToolCallItem, ToolCallOutputItem
from models import TradeResult


@pytest.mark.asyncio
class TestAgentExecutorInitialization:
    """Test AgentExecutor initialization."""

    def test_init(self, sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy, sample_model_name):
        """Test AgentExecutor initialization sets up state correctly."""
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy, sample_model_name)

        assert executor.agent_id == sample_agent_id
        assert executor.name == sample_agent_name
        assert executor.agent_style == sample_agent_style
        assert executor.strategy == sample_strategy
        assert executor.model_name == sample_model_name
        assert executor.current_run_id is None
        assert executor.trade_count == 0
        assert executor.last_decision is None
        assert executor.tracker is None
        # New phase data tracking
        assert executor.research_start_time is None
        assert executor.decision_start_time is None
        assert executor.research_candidates == []
        assert executor.research_sources == []


@pytest.mark.asyncio
class TestAgentExecutorPhase1StartRun:
    """Test Phase 1: Initialize cycle."""

    @patch("agent_executor.initialize_agent")
    @patch("agent_executor._get_balance_raw")
    @patch("agent_executor._get_holdings_raw")
    @patch("agent_executor.create_run")
    @patch("agent_executor.update_phase")
    @patch("agent_executor.broadcast_status")
    @patch("agent_executor.ToolTracker")
    async def test_phase1_start_run_success(
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
        """Test Phase 1 creates run and transitions to RESEARCHING."""
        # Setup mocks
        mock_initialize.return_value = None
        mock_get_balance.return_value = sample_balance
        mock_get_holdings.return_value = sample_holdings
        mock_create_run.return_value = 123  # Sample run ID
        mock_update_phase.return_value = True
        mock_tracker_instance = MagicMock()
        mock_tracker_class.return_value = mock_tracker_instance

        # Create executor
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)

        # Execute Phase 1
        run_id = await executor._phase1_start_run()

        # Verify results
        assert run_id == 123
        assert executor.current_run_id == 123
        assert executor.trade_count == 0
        assert executor.tracker is not None
        assert executor.research_start_time is not None

        # Verify API calls
        mock_initialize.assert_called_once_with(sample_agent_name)
        mock_get_balance.assert_called_once_with(sample_agent_id)
        mock_get_holdings.assert_called_once_with(sample_agent_id)

        # Verify run creation and phase update
        mock_create_run.assert_called_once_with(sample_agent_id)
        mock_update_phase.assert_called_once_with(123, "RESEARCHING")

        # Verify broadcast called (INITIALIZING + RESEARCHING)
        assert mock_broadcast.call_count >= 2

        # Verify tracker initialized
        mock_tracker_class.assert_called_once_with(123)
        assert mock_tracker_instance.log_data_access.call_count >= 1

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
        # Setup mocks
        mock_initialize.return_value = None
        mock_create_run.return_value = None  # Simulate failure

        # Create executor
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)

        # Execute Phase 1 - should raise exception
        with pytest.raises(Exception) as exc_info:
            await executor._phase1_start_run()

        assert "Failed to create run" in str(exc_info.value)


@pytest.mark.asyncio
class TestAgentExecutorPhase2PrepareContext:
    """Test Phase 2: Prepare context."""

    @patch("agent_executor.get_recent_activity")
    async def test_phase2_prepare_context_with_history(
        self,
        mock_get_recent_activity,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_recent_activity,
    ):
        """Test Phase 2 prepares baseline context without steering."""
        # Setup mocks
        mock_get_recent_activity.return_value = sample_recent_activity

        # Create executor
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)

        # Execute Phase 2
        context = await executor._phase2_prepare_context()

        # Verify results - only baseline context, no steering
        assert "historical_context" in context
        assert "research_focus" not in context  # Removed - no longer steering
        assert context["historical_context"] == sample_recent_activity

        # Verify API calls - only recent activity
        mock_get_recent_activity.assert_called_once_with(sample_agent_name, days=30)

        # Verify research source added
        assert len(executor.research_sources) == 1
        assert executor.research_sources[0].type == "system_context"

    @patch("agent_executor.get_recent_activity")
    async def test_phase2_prepare_context_no_history(
        self,
        mock_get_recent_activity,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
    ):
        """Test Phase 2 handles no historical data gracefully."""
        # Setup mocks - no history
        mock_get_recent_activity.return_value = '{"error": "No recent activity found"}'

        # Create executor
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)

        # Execute Phase 2
        context = await executor._phase2_prepare_context()

        # Verify results - only baseline context (even if empty)
        assert "historical_context" in context
        assert "research_focus" not in context  # Removed - no longer steering
        assert context["historical_context"] == '{"error": "No recent activity found"}'


@pytest.mark.asyncio
class TestAgentExecutorPhase3MarketAnalyst:
    """Test Phase 3: Market Analyst agent."""

    @patch("agent_executor.create_market_analyst_agent")
    @patch("agent_executor.Runner")
    @patch("agent_executor._get_balance_raw")
    @patch("agent_executor._get_holdings_raw")
    async def test_phase3_run_market_analyst_success(
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
        """Test Phase 3 runs Market Analyst and extracts ResearchResponse."""
        # Setup mocks
        mock_get_balance.return_value = 100000.0
        mock_get_holdings.return_value = []

        mock_analyst = MagicMock()
        mock_create_analyst.return_value = mock_analyst

        mock_result = MagicMock()
        mock_result.output = sample_research_response
        mock_runner_class.run = AsyncMock(return_value=mock_result)

        context = {"historical_context": "{}"}

        # Create executor
        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy, sample_model_name
        )
        executor.current_run_id = 123
        executor.tracker = MagicMock()

        # Execute Phase 3
        research_response = await executor._phase3_run_market_analyst(mock_mcp_pool, context)

        # Verify Market Analyst created with correct parameters
        mock_create_analyst.assert_called_once()
        call_args = mock_create_analyst.call_args
        assert call_args[1]["agent_name"] == sample_agent_name
        assert call_args[1]["agent_style"] == sample_agent_style
        assert call_args[1]["strategy"] == sample_strategy
        assert call_args[1]["mcp_pool"] == mock_mcp_pool
        assert call_args[1]["model_name"] == sample_model_name

        # Verify Runner called
        mock_runner_class.run.assert_called_once()

        # Verify ResearchResponse returned
        assert research_response == sample_research_response
        assert len(research_response.sources) == 3


@pytest.mark.asyncio
class TestAgentExecutorPhase4DecisionMaker:
    """Test Phase 4: Decision Maker agent."""

    @patch("agent_executor.create_decision_maker_agent")
    @patch("agent_executor.Runner")
    @patch("agent_executor.update_phase")
    @patch("agent_executor._get_balance_raw")
    @patch("agent_executor._get_holdings_raw")
    async def test_phase4_run_decision_maker_success(
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
        """Test Phase 4 runs Decision Maker with Market Analyst results."""
        # Setup mocks
        mock_get_balance.return_value = 100000.0
        mock_get_holdings.return_value = []
        mock_update_phase.return_value = True

        mock_decision_maker = MagicMock()
        mock_create_decision_maker.return_value = mock_decision_maker

        mock_result = MagicMock()
        mock_runner_class.run = AsyncMock(return_value=mock_result)

        context = {"historical_context": "{}"}

        # Create executor
        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy, sample_model_name
        )
        executor.current_run_id = 123
        executor.tracker = MagicMock()
        from datetime import datetime
        executor.decision_start_time = datetime.now()

        # Pre-set decision (simulating decide_action tool being called during Runner.run)
        executor.last_decision = sample_decision

        # Execute Phase 4
        await executor._phase4_run_decision_maker(
            mock_mcp_pool, sample_research_response, context, force_trade=False
        )

        # Verify phase updated to DECIDING
        mock_update_phase.assert_called_once_with(123, "DECIDING")

        # Verify Decision Maker created with correct parameters
        mock_create_decision_maker.assert_called_once()
        call_args = mock_create_decision_maker.call_args
        assert call_args[1]["agent_name"] == sample_agent_name
        assert call_args[1]["agent_style"] == sample_agent_style
        assert call_args[1]["strategy"] == sample_strategy
        assert call_args[1]["executor"] == executor
        assert call_args[1]["mcp_pool"] == mock_mcp_pool
        assert call_args[1]["model_name"] == sample_model_name

        # Verify Runner called (should include research results in prompt)
        mock_runner_class.run.assert_called_once()

        # Verify decision was stored
        assert executor.last_decision is not None


@pytest.mark.asyncio
class TestAgentExecutorPhase5ValidateResults:
    """Test Phase 5: Validate results."""

    async def test_phase5_validate_results_with_decision(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_decision,
    ):
        """Test Phase 5 validates successfully when decision exists."""
        # Create executor with decision
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)
        executor.last_decision = sample_decision

        # Execute Phase 5 - should not raise
        await executor._phase5_validate_results()

    async def test_phase5_validate_results_no_decision(
        self,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
    ):
        """Test Phase 5 raises error when no decision recorded."""
        # Create executor without decision
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)
        executor.last_decision = None

        # Execute Phase 5 - should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            await executor._phase5_validate_results()

        assert "no decision was recorded" in str(exc_info.value)


@pytest.mark.asyncio
class TestAgentExecutorPhase6ExecuteDecision:
    """Test Phase 6: Execute decision."""

    @patch("agent_executor.buy_shares")
    @patch("agent_executor.update_phase")
    @patch("agent_executor.broadcast_status")
    async def test_phase6_execute_buy_decision(
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
        """Test Phase 6 executes BUY decision."""
        # Setup mocks - TradeResult matches backend Java DTO
        mock_buy.return_value = TradeResult(
            tradeId=101, symbol="NVDA", quantity=50, price=142.50, newBalance=92875.00
        )
        mock_update_phase.return_value = True

        # Create executor with decision
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)
        executor.current_run_id = 123
        executor.last_decision = sample_decision
        executor.tracker = MagicMock()

        # Execute Phase 6
        await executor._phase6_execute_decision()

        # Verify phase updated to TRADING
        mock_update_phase.assert_called_once_with(123, "TRADING")

        # Verify trade executed
        mock_buy.assert_called_once_with(
            sample_agent_id, "NVDA", 50, runId=123, agent_name=sample_agent_name
        )
        assert executor.trade_count == 1
        assert executor.trade_id == 101  # Verify tradeId captured

        # Verify execution status set
        from models.run_tracking import PhaseStatus
        assert executor.execution_status == PhaseStatus.COMPLETED

        # Verify broadcasts
        assert mock_broadcast.call_count >= 1

        # Verify tracker logged execution
        assert executor.tracker.log_reasoning.call_count >= 1

    @patch("agent_executor.sell_shares")
    @patch("agent_executor.update_phase")
    @patch("agent_executor.broadcast_status")
    async def test_phase6_execute_sell_decision(
        self,
        mock_broadcast,
        mock_update_phase,
        mock_sell,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
    ):
        """Test Phase 6 executes SELL decision."""
        # Setup mocks - TradeResult matches backend Java DTO
        mock_sell.return_value = TradeResult(
            tradeId=102, symbol="AAPL", quantity=25, price=185.00, newBalance=104625.00
        )
        mock_update_phase.return_value = True

        # Create SELL decision
        from models import TradingDecision
        sell_decision = TradingDecision(
            action="SELL",
            symbol="AAPL",
            quantity=25,
            rationale="Taking profits",
            fullReasoning="AAPL has reached target price.",
            researchSources="[]",
            historicalContext="[]",
        )

        # Create executor with decision
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)
        executor.current_run_id = 123
        executor.last_decision = sell_decision
        executor.tracker = MagicMock()

        # Execute Phase 6
        await executor._phase6_execute_decision()

        # Verify trade executed
        mock_sell.assert_called_once_with(
            sample_agent_id, "AAPL", 25, runId=123, agent_name=sample_agent_name
        )
        assert executor.trade_count == 1

    @patch("agent_executor.broadcast_status")
    async def test_phase6_execute_hold_decision(
        self, mock_broadcast, sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy
    ):
        """Test Phase 6 handles HOLD decision."""
        # Create HOLD decision
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

        # Create executor with decision
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)
        executor.current_run_id = 123
        executor.last_decision = hold_decision
        executor.tracker = MagicMock()

        # Execute Phase 6
        await executor._phase6_execute_decision()

        # Verify no trade executed
        assert executor.trade_count == 0

        # Verify execution status is SKIPPED
        from models.run_tracking import PhaseStatus
        assert executor.execution_status == PhaseStatus.SKIPPED

        # Verify tracker logged HOLD decision
        assert executor.tracker.log_reasoning.call_count >= 1
        call_args = executor.tracker.log_reasoning.call_args_list
        assert any("HOLD" in str(call) for call in call_args)

    @patch("agent_executor.buy_shares")
    @patch("agent_executor.update_phase")
    @patch("agent_executor.broadcast_status")
    async def test_phase6_handles_trade_failure(
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
        """Test Phase 6 handles trade execution failure gracefully."""
        # Setup mocks - trade fails
        mock_buy.side_effect = Exception("Insufficient funds")
        mock_update_phase.return_value = True

        # Create executor with decision
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)
        executor.current_run_id = 123
        executor.last_decision = sample_decision
        executor.tracker = MagicMock()

        # Execute Phase 6 - should not raise, just log
        await executor._phase6_execute_decision()

        # Verify trade was attempted
        mock_buy.assert_called_once()

        # Verify trade count not incremented
        assert executor.trade_count == 0

        # Verify execution status is FAILED
        from models.run_tracking import PhaseStatus
        assert executor.execution_status == PhaseStatus.FAILED
        assert executor.execution_error == "Insufficient funds"

        # Verify tracker logged failure
        assert executor.tracker.log_reasoning.call_count >= 1
        call_args = executor.tracker.log_reasoning.call_args_list
        assert any("Failed" in str(call) for call in call_args)


@pytest.mark.asyncio
class TestAgentExecutorPhase7Finalize:
    """Test Phase 7: Finalize cycle."""

    @patch("agent_executor.complete_run")
    @patch("agent_executor.broadcast_status")
    async def test_phase7_finalize_with_trade(
        self,
        mock_broadcast,
        mock_complete_run,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
        sample_decision,
    ):
        """Test Phase 7 finalizes cycle with trade."""
        # Setup mocks
        mock_complete_run.return_value = True

        # Create executor with completed trade
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)
        executor.last_decision = sample_decision
        executor.trade_count = 1
        from datetime import datetime
        executor.research_start_time = datetime.now()
        executor.decision_start_time = datetime.now()
        from models.run_tracking import PhaseStatus
        executor.execution_status = PhaseStatus.COMPLETED

        # Execute Phase 7
        await executor._phase7_finalize(run_id=123)

        # Verify complete_run called
        mock_complete_run.assert_called_once()
        call_args = mock_complete_run.call_args
        assert call_args[0][0] == 123  # run_id
        complete_data = call_args[0][1]
        assert complete_data.decision.value == "BUY"
        assert complete_data.symbol == "NVDA"
        assert complete_data.quantity == 50
        assert complete_data.executionStatus == PhaseStatus.COMPLETED

        # Verify broadcast called with completion status
        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args
        assert "Completed" in call_args[0][3]
        assert call_args[0][4] == 100  # progress

    @patch("agent_executor.complete_run")
    @patch("agent_executor.broadcast_status")
    async def test_phase7_finalize_no_trade(
        self, mock_broadcast, mock_complete_run, sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy
    ):
        """Test Phase 7 finalizes cycle with HOLD."""
        # Setup mocks
        mock_complete_run.return_value = True

        # Create executor with HOLD decision
        from models import TradingDecision
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)
        executor.last_decision = TradingDecision(
            action="HOLD",
            symbol="",
            quantity=0,
            rationale="Portfolio unchanged",
            fullReasoning="No trades needed.",
            researchSources="[]",
            historicalContext="[]",
        )
        executor.trade_count = 0
        from datetime import datetime
        executor.research_start_time = datetime.now()
        executor.decision_start_time = datetime.now()
        from models.run_tracking import PhaseStatus
        executor.execution_status = PhaseStatus.SKIPPED

        # Execute Phase 7
        await executor._phase7_finalize(run_id=123)

        # Verify complete_run called
        mock_complete_run.assert_called_once()
        call_args = mock_complete_run.call_args
        complete_data = call_args[0][1]
        assert complete_data.decision.value == "HOLD"
        assert complete_data.executionStatus == PhaseStatus.SKIPPED

        # Verify broadcast shows no trades
        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args
        assert "No trades" in call_args[0][3] or "HOLD" in str(call_args)


@pytest.mark.asyncio
class TestAgentExecutorErrorHandling:
    """Test error handling."""

    @patch("agent_executor.update_phase")
    @patch("agent_executor.complete_run")
    @patch("agent_executor.broadcast_status")
    async def test_handle_cycle_error(
        self,
        mock_broadcast,
        mock_complete_run,
        mock_update_phase,
        sample_agent_id,
        sample_agent_name,
        sample_agent_style,
        sample_strategy,
    ):
        """Test error handling broadcasts and marks run."""
        # Setup mocks
        mock_update_phase.return_value = True
        mock_complete_run.return_value = True

        # Create executor
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)

        # Execute error handler
        error = Exception("Test error")
        await executor._handle_cycle_error(error, run_id=123)

        # Verify error broadcast
        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args
        assert "Error" in call_args[0][3]
        assert "Test error" in call_args[0][3]

        # Verify phase updated to ERROR
        mock_update_phase.assert_called_once_with(123, "ERROR")

        # Verify complete_run called with error data
        mock_complete_run.assert_called_once()
        call_args = mock_complete_run.call_args
        complete_data = call_args[0][1]
        assert complete_data.errorDetails == "Test error"
        from models.run_tracking import PhaseStatus
        assert complete_data.executionStatus == PhaseStatus.FAILED


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
        """Test full execution cycle with BUY decision using two-agent architecture."""
        # Setup mocks
        mock_initialize.return_value = None
        mock_get_balance.return_value = sample_balance
        mock_get_holdings.return_value = sample_holdings
        mock_create_run.return_value = 123
        mock_update_phase.return_value = True
        mock_complete_run.return_value = True
        mock_get_recent_activity.return_value = sample_recent_activity
        # TradeResult matches backend Java DTO
        mock_buy.return_value = TradeResult(
            tradeId=103, symbol="NVDA", quantity=50, price=142.50, newBalance=92875.00
        )

        # Mock tracker
        mock_tracker_instance = MagicMock()
        mock_tracker_class.return_value = mock_tracker_instance

        # Create executor
        executor = AgentExecutor(
            sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy, sample_model_name
        )

        # Mock the two-agent phases
        mock_phase3 = mocker.patch.object(
            executor, "_phase3_run_market_analyst", return_value=sample_research_response
        )

        # Mock Phase 4 to set decision
        async def mock_phase4_side_effect(mcp_pool, research_response, context, force_trade):
            executor.store_decision(
                action="BUY",
                symbol="NVDA",
                quantity=50,
                rationale="AI growth",
                full_reasoning="Strong fundamentals",
                research_sources=json.dumps({"summary": "NVDA analysis", "sources": []}),
                historical_context=json.dumps({"summary": "No prior trades", "insights": []}),
            )

        mock_phase4 = mocker.patch.object(
            executor, "_phase4_run_decision_maker", side_effect=mock_phase4_side_effect
        )

        # Execute full cycle
        result = await executor.execute_cycle(
            mcp_pool=mock_mcp_pool,
            force_trade=False,
        )

        # Verify result
        assert result["decision"].action == "BUY"
        assert result["trade_count"] == 1
        assert result["run_id"] == 123

        # Verify all phases executed
        mock_initialize.assert_called_once()
        mock_create_run.assert_called_once()
        mock_update_phase.assert_called()  # Multiple phase updates
        mock_get_recent_activity.assert_called_once()

        # Verify two-agent flow
        mock_phase3.assert_called_once()  # Market Analyst
        mock_phase4.assert_called_once()  # Decision Maker

        mock_buy.assert_called_once()
        mock_complete_run.assert_called_once()

        # Verify cleanup
        assert executor.current_run_id is None
        assert executor.trade_count == 0
        assert executor.last_decision is None
        assert executor.tracker is None

    @patch("agent_executor.initialize_agent")
    @patch("agent_executor._get_balance_raw")
    @patch("agent_executor._get_holdings_raw")
    @patch("agent_executor.create_run")
    @patch("agent_executor.update_phase")
    @patch("agent_executor.complete_run")
    @patch("agent_executor.broadcast_status")
    @patch("agent_executor.ToolTracker")
    async def test_execute_cycle_handles_error(
        self,
        mock_tracker_class,
        mock_broadcast,
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
        mock_mcp_pool,
        mocker,
    ):
        """Test full cycle handles errors and cleans up."""
        # Setup mocks
        mock_initialize.return_value = None
        mock_get_balance.return_value = 100000.0
        mock_get_holdings.return_value = []
        mock_create_run.return_value = 123
        mock_update_phase.return_value = True
        mock_complete_run.return_value = True

        # Mock tracker
        mock_tracker_instance = MagicMock()
        mock_tracker_class.return_value = mock_tracker_instance

        # Create executor
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy)

        # Mock Phase 3 to raise error
        mocker.patch.object(
            executor, "_phase3_run_market_analyst", side_effect=Exception("Market Analyst failed")
        )

        # Execute cycle - should raise error
        with pytest.raises(Exception) as exc_info:
            await executor.execute_cycle(
                mcp_pool=mock_mcp_pool,
                force_trade=False,
            )

        assert "Market Analyst failed" in str(exc_info.value)

        # Verify error handling - update_phase to ERROR
        assert any(call[0] == (123, "ERROR") for call in mock_update_phase.call_args_list)

        # Verify complete_run called with error data
        mock_complete_run.assert_called()

        # Verify cleanup still happened
        assert executor.current_run_id is None
        assert executor.trade_count == 0
        assert executor.last_decision is None
        assert executor.tracker is None


@pytest.mark.asyncio
class TestAgentExecutorHelperMethods:
    """Test helper methods."""

    def test_store_decision(
        self, sample_agent_id, sample_agent_name, sample_agent_style, sample_strategy
    ):
        """Test decision storage."""
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

        assert executor.last_decision is not None
        assert executor.last_decision.action == "BUY"
        assert executor.last_decision.symbol == "AAPL"
        assert executor.last_decision.quantity == 100
        assert executor.last_decision.researchSources == '{"summary": "test"}'
