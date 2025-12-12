"""Comprehensive tests for AgentExecutor class.

Tests follow the pattern from grounding research:
- Mock tool execution functions (not the LLM)
- Use aioresponses for HTTP mocking
- Test behavior, not implementation details
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from agent_executor import AgentExecutor


@pytest.mark.asyncio
class TestAgentExecutorInitialization:
    """Test AgentExecutor initialization."""

    def test_init(self, sample_agent_id, sample_agent_name, sample_strategy):
        """Test AgentExecutor initialization sets up state correctly."""
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)

        assert executor.agent_id == sample_agent_id
        assert executor.name == sample_agent_name
        assert executor.strategy == sample_strategy
        assert executor.current_run_id is None
        assert executor.trade_count == 0
        assert executor.last_decision is None
        assert executor.tracker is None


@pytest.mark.asyncio
class TestAgentExecutorPhase1Initialize:
    """Test Phase 1: Initialize cycle."""

    @patch("agent_executor.initialize_agent")
    @patch("agent_executor.get_account_report")
    @patch("agent_executor._get_balance_raw")
    @patch("agent_executor._get_holdings_raw")
    @patch("agent_executor.start_run")
    @patch("agent_executor.broadcast_status")
    @patch("agent_executor.ToolTracker")
    async def test_phase1_initialize_success(
        self,
        mock_tracker_class,
        mock_broadcast,
        mock_start_run,
        mock_get_holdings,
        mock_get_balance,
        mock_get_account,
        mock_initialize,
        sample_agent_id,
        sample_agent_name,
        sample_strategy,
        sample_balance,
        sample_holdings,
    ):
        """Test Phase 1 initializes tracking and broadcasts status."""
        # Setup mocks
        mock_initialize.return_value = None
        mock_get_account.return_value = "Account report"
        mock_get_balance.return_value = sample_balance
        mock_get_holdings.return_value = sample_holdings
        mock_start_run.return_value = 123  # Sample run ID
        mock_tracker_instance = MagicMock()
        mock_tracker_class.return_value = mock_tracker_instance

        # Create executor
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)

        # Execute Phase 1
        run_id = await executor._phase1_initialize("TRADING", "trading")

        # Verify results
        assert run_id == 123
        assert executor.current_run_id == 123
        assert executor.trade_count == 0
        assert executor.last_decision is None
        assert executor.tracker is not None

        # Verify API calls
        mock_initialize.assert_called_once_with(sample_agent_name)
        mock_get_account.assert_called_once_with(sample_agent_id)
        mock_get_balance.assert_called_once_with(sample_agent_id)
        mock_get_holdings.assert_called_once_with(sample_agent_id)

        # Verify broadcast called
        assert mock_broadcast.call_count >= 1

        # Verify run tracking started
        mock_start_run.assert_called_once()
        call_args = mock_start_run.call_args
        assert call_args[0][0] == sample_agent_id
        assert call_args[0][1] == sample_agent_name
        assert call_args[0][2] == "TRADING"

        # Verify tracker initialized
        mock_tracker_class.assert_called_once_with(123)
        assert mock_tracker_instance.log_data_access.call_count >= 1
        assert mock_tracker_instance.log_reasoning.call_count >= 1

    @patch("agent_executor.initialize_agent")
    @patch("agent_executor.start_run")
    @patch("agent_executor.broadcast_status")
    @patch("agent_executor._get_balance_raw")
    @patch("agent_executor._get_holdings_raw")
    @patch("agent_executor.get_account_report")
    async def test_phase1_initialize_fails_without_run_id(
        self,
        mock_get_account,
        mock_get_holdings,
        mock_get_balance,
        mock_broadcast,
        mock_start_run,
        mock_initialize,
        sample_agent_id,
        sample_agent_name,
        sample_strategy,
    ):
        """Test Phase 1 raises error if run tracking fails."""
        # Setup mocks
        mock_initialize.return_value = None
        mock_get_account.return_value = "Account report"
        mock_get_balance.return_value = 100000.0
        mock_get_holdings.return_value = []
        mock_start_run.return_value = None  # Simulate failure

        # Create executor
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)

        # Execute Phase 1 - should raise exception
        with pytest.raises(Exception) as exc_info:
            await executor._phase1_initialize("TRADING", "trading")

        assert "Failed to start run tracking" in str(exc_info.value)


@pytest.mark.asyncio
class TestAgentExecutorPhase2PrepareContext:
    """Test Phase 2: Prepare context."""

    @patch("agent_executor.get_recent_activity")
    @patch("agent_executor._get_holdings_raw")
    @patch("agent_executor.broadcast_status")
    async def test_phase2_prepare_context_with_history(
        self,
        mock_broadcast,
        mock_get_holdings,
        mock_get_recent_activity,
        sample_agent_id,
        sample_agent_name,
        sample_strategy,
        sample_recent_activity,
        sample_holdings,
    ):
        """Test Phase 2 prepares context with historical data."""
        # Setup mocks
        mock_get_recent_activity.return_value = sample_recent_activity
        mock_get_holdings.return_value = sample_holdings

        # Create executor
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)

        # Execute Phase 2
        context = await executor._phase2_prepare_context()

        # Verify results
        assert "historical_context" in context
        assert "research_focus" in context
        assert context["historical_context"] == sample_recent_activity
        assert "NVDA" in context["research_focus"]  # From sample_recent_activity
        assert "AAPL" in context["research_focus"]  # From sample_holdings

        # Verify API calls
        mock_get_recent_activity.assert_called_once_with(sample_agent_name, days=30)
        mock_get_holdings.assert_called_once_with(sample_agent_id)
        mock_broadcast.assert_called_once()

    @patch("agent_executor.get_recent_activity")
    @patch("agent_executor._get_holdings_raw")
    @patch("agent_executor.broadcast_status")
    async def test_phase2_prepare_context_no_history(
        self,
        mock_broadcast,
        mock_get_holdings,
        mock_get_recent_activity,
        sample_agent_id,
        sample_agent_name,
        sample_strategy,
    ):
        """Test Phase 2 handles no historical data gracefully."""
        # Setup mocks - no history
        mock_get_recent_activity.return_value = '{"error": "No recent activity found"}'
        mock_get_holdings.return_value = []

        # Create executor
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)

        # Execute Phase 2
        context = await executor._phase2_prepare_context()

        # Verify results
        assert "historical_context" in context
        assert "research_focus" in context
        assert context["research_focus"] == ""  # No symbols to research


@pytest.mark.asyncio
class TestAgentExecutorPhase3CreateAgent:
    """Test Phase 3: Create agent."""

    async def test_phase3_create_agent(
        self, sample_agent_id, sample_agent_name, sample_strategy
    ):
        """Test Phase 3 delegates agent creation to tool factory."""
        # Create mock tool factory
        mock_tool_factory = MagicMock()
        mock_agent = MagicMock()
        mock_tool_factory.create_agent = AsyncMock(return_value=mock_agent)

        # Create executor
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)

        # Execute Phase 3
        agent = await executor._phase3_create_agent(mock_tool_factory)

        # Verify results
        assert agent == mock_agent
        mock_tool_factory.create_agent.assert_called_once_with(executor)


@pytest.mark.asyncio
class TestAgentExecutorPhase4RunAgent:
    """Test Phase 4: Run agent."""

    @patch("agent_executor.Runner")
    async def test_phase4_run_agent(
        self, mock_runner_class, sample_agent_id, sample_agent_name, sample_strategy
    ):
        """Test Phase 4 runs agent with generated message."""
        # Setup mocks
        mock_agent = MagicMock()
        mock_message_builder = MagicMock()
        mock_message_builder.build_message.return_value = "Test message"
        mock_result = MagicMock()
        mock_runner_class.run = AsyncMock(return_value=mock_result)

        context = {
            "historical_context": "{}",
            "research_focus": "Focus on AAPL",
        }

        # Create executor
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)

        # Execute Phase 4
        result = await executor._phase4_run_agent(
            mock_agent, mock_message_builder, context, force_trade=False
        )

        # Verify results
        assert result == mock_result
        mock_message_builder.build_message.assert_called_once_with(
            "{}", "Focus on AAPL", False
        )
        mock_runner_class.run.assert_called_once_with(
            mock_agent, "Test message", max_turns=30
        )


@pytest.mark.asyncio
class TestAgentExecutorPhase5ParseResults:
    """Test Phase 5: Parse results."""

    async def test_phase5_parse_results_with_researcher(
        self, sample_agent_id, sample_agent_name, sample_strategy
    ):
        """Test Phase 5 parses Researcher tool usage and extracts sources."""
        # Create mock result with Researcher tool call
        mock_result = MagicMock()

        # Create mock tool message (Researcher tool result)
        tool_msg = MagicMock()
        tool_msg.role = "tool"
        tool_msg.name = "Researcher"
        tool_msg.content = """NVDA shows strong growth. [SOURCE: TechNews](https://example.com/nvda)"""

        # Create mock assistant message (tool call request)
        assistant_msg = MagicMock()
        assistant_msg.role = "assistant"
        assistant_msg.content = "Analyzing NVDA..."
        assistant_msg.tool_calls = [MagicMock()]
        assistant_msg.tool_calls[0].function = MagicMock()
        assistant_msg.tool_calls[0].function.arguments = json.dumps(
            {"query": "Research NVDA AI chip market"}
        )

        # Create final assistant message
        final_msg = MagicMock()
        final_msg.role = "assistant"
        final_msg.content = "Based on my research, NVDA looks strong."

        mock_result.messages = [assistant_msg, tool_msg, final_msg]

        # Create executor with tracker
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)
        executor.tracker = MagicMock()

        # Execute Phase 5
        await executor._phase5_parse_results(mock_result)

        # Verify tracker logged tool call
        assert executor.tracker.log_tool_call.call_count >= 1
        # Verify tracker logged research query
        assert executor.tracker.log_research_query.call_count >= 1
        # Verify tracker logged research phase
        assert executor.tracker.log_reasoning.call_count >= 1

    async def test_phase5_parse_results_no_tools(
        self, sample_agent_id, sample_agent_name, sample_strategy
    ):
        """Test Phase 5 handles results with no tool usage."""
        # Create mock result with only assistant messages
        mock_result = MagicMock()
        assistant_msg = MagicMock()
        assistant_msg.role = "assistant"
        assistant_msg.content = "I decide to HOLD."
        mock_result.messages = [assistant_msg]

        # Create executor with tracker
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)
        executor.tracker = MagicMock()

        # Execute Phase 5
        await executor._phase5_parse_results(mock_result)

        # Verify tracker logged reasoning (but no tool calls)
        assert executor.tracker.log_reasoning.call_count >= 1
        assert executor.tracker.log_tool_call.call_count == 0


@pytest.mark.asyncio
class TestAgentExecutorPhase6ExecuteDecision:
    """Test Phase 6: Execute decision."""

    @patch("agent_executor.buy_shares")
    @patch("agent_executor.broadcast_status")
    async def test_phase6_execute_buy_decision(
        self,
        mock_broadcast,
        mock_buy,
        sample_agent_id,
        sample_agent_name,
        sample_strategy,
        sample_decision,
    ):
        """Test Phase 6 executes BUY decision."""
        # Setup mocks
        mock_buy.return_value = None

        # Create executor with decision
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)
        executor.current_run_id = 123
        executor.last_decision = sample_decision
        executor.tracker = MagicMock()

        # Execute Phase 6
        await executor._phase6_execute_decision()

        # Verify trade executed
        mock_buy.assert_called_once_with(
            sample_agent_id, "NVDA", 50, runId=123, agent_name=sample_agent_name
        )
        assert executor.trade_count == 1

        # Verify broadcasts
        assert mock_broadcast.call_count >= 2  # DECIDING + TRADING

        # Verify tracker logged decision and execution
        assert executor.tracker.log_reasoning.call_count >= 2

    @patch("agent_executor.sell_shares")
    @patch("agent_executor.broadcast_status")
    async def test_phase6_execute_sell_decision(
        self,
        mock_broadcast,
        mock_sell,
        sample_agent_id,
        sample_agent_name,
        sample_strategy,
    ):
        """Test Phase 6 executes SELL decision."""
        # Setup mocks
        mock_sell.return_value = None

        # Create SELL decision
        sell_decision = {
            "action": "SELL",
            "symbol": "AAPL",
            "quantity": 25,
            "rationale": "Taking profits",
            "fullReasoning": "AAPL has reached target price.",
            "researchSources": "[]",
            "historicalContext": "[]",
        }

        # Create executor with decision
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)
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
        self, mock_broadcast, sample_agent_id, sample_agent_name, sample_strategy
    ):
        """Test Phase 6 handles HOLD decision."""
        # Create HOLD decision
        hold_decision = {
            "action": "HOLD",
            "symbol": "",
            "quantity": 0,
            "rationale": "Portfolio looks good",
            "fullReasoning": "No changes needed.",
            "researchSources": "[]",
            "historicalContext": "[]",
        }

        # Create executor with decision
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)
        executor.current_run_id = 123
        executor.last_decision = hold_decision
        executor.tracker = MagicMock()

        # Execute Phase 6
        await executor._phase6_execute_decision()

        # Verify no trade executed
        assert executor.trade_count == 0

        # Verify tracker logged HOLD decision
        assert executor.tracker.log_reasoning.call_count >= 1
        call_args = executor.tracker.log_reasoning.call_args_list
        assert any("HOLD" in str(call) for call in call_args)

    @patch("agent_executor.buy_shares")
    @patch("agent_executor.broadcast_status")
    async def test_phase6_handles_trade_failure(
        self,
        mock_broadcast,
        mock_buy,
        sample_agent_id,
        sample_agent_name,
        sample_strategy,
        sample_decision,
    ):
        """Test Phase 6 handles trade execution failure gracefully."""
        # Setup mocks - trade fails
        mock_buy.side_effect = Exception("Insufficient funds")

        # Create executor with decision
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)
        executor.current_run_id = 123
        executor.last_decision = sample_decision
        executor.tracker = MagicMock()

        # Execute Phase 6 - should not raise, just log
        await executor._phase6_execute_decision()

        # Verify trade was attempted
        mock_buy.assert_called_once()

        # Verify trade count not incremented
        assert executor.trade_count == 0

        # Verify tracker logged failure
        assert executor.tracker.log_reasoning.call_count >= 2
        call_args = executor.tracker.log_reasoning.call_args_list
        assert any("Failed" in str(call) for call in call_args)


@pytest.mark.asyncio
class TestAgentExecutorPhase7Finalize:
    """Test Phase 7: Finalize cycle."""

    @patch("agent_executor.end_run")
    @patch("agent_executor.broadcast_status")
    async def test_phase7_finalize_with_trade(
        self,
        mock_broadcast,
        mock_end_run,
        sample_agent_id,
        sample_agent_name,
        sample_strategy,
        sample_decision,
    ):
        """Test Phase 7 finalizes cycle with trade."""
        # Setup mocks
        mock_end_run.return_value = None

        # Create executor with completed trade
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)
        executor.last_decision = sample_decision
        executor.trade_count = 1

        # Execute Phase 7
        await executor._phase7_finalize(run_id=123)

        # Verify end_run called with correct data
        mock_end_run.assert_called_once()
        call_args = mock_end_run.call_args
        assert call_args[0][0] == 123  # run_id
        assert "Strong AI growth potential" in call_args[0][1]  # summary (rationale)
        assert call_args[0][5] == 1  # trade_count

        # Verify broadcast called with completion status
        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args
        assert "Completed" in call_args[0][3]
        assert call_args[0][4] == 100  # progress

    @patch("agent_executor.end_run")
    @patch("agent_executor.broadcast_status")
    async def test_phase7_finalize_no_trade(
        self, mock_broadcast, mock_end_run, sample_agent_id, sample_agent_name, sample_strategy
    ):
        """Test Phase 7 finalizes cycle with HOLD."""
        # Setup mocks
        mock_end_run.return_value = None

        # Create executor with HOLD decision
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)
        executor.last_decision = {
            "action": "HOLD",
            "rationale": "Portfolio unchanged",
            "fullReasoning": "No trades needed.",
            "researchSources": "[]",
            "historicalContext": "[]",
        }
        executor.trade_count = 0

        # Execute Phase 7
        await executor._phase7_finalize(run_id=123)

        # Verify end_run called
        mock_end_run.assert_called_once()
        call_args = mock_end_run.call_args
        assert call_args[0][5] == 0  # trade_count

        # Verify broadcast shows no trades
        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args
        assert "No trades" in call_args[0][3] or "HOLD" in str(call_args)


@pytest.mark.asyncio
class TestAgentExecutorErrorHandling:
    """Test error handling."""

    @patch("agent_executor.mark_run_as_error")
    @patch("agent_executor.broadcast_status")
    async def test_handle_cycle_error(
        self,
        mock_broadcast,
        mock_mark_error,
        sample_agent_id,
        sample_agent_name,
        sample_strategy,
    ):
        """Test error handling broadcasts and marks run."""
        # Setup mocks
        mock_mark_error.return_value = None

        # Create executor
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)

        # Execute error handler
        error = Exception("Test error")
        await executor._handle_cycle_error(error, run_id=123)

        # Verify error broadcast
        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args
        assert "Error" in call_args[0][3]
        assert "Test error" in call_args[0][3]

        # Verify run marked as error
        mock_mark_error.assert_called_once_with(123, "Test error")


@pytest.mark.asyncio
class TestAgentExecutorFullCycle:
    """Test full execution cycle integration."""

    @patch("agent_executor.initialize_agent")
    @patch("agent_executor.get_account_report")
    @patch("agent_executor._get_balance_raw")
    @patch("agent_executor._get_holdings_raw")
    @patch("agent_executor.start_run")
    @patch("agent_executor.end_run")
    @patch("agent_executor.get_recent_activity")
    @patch("agent_executor.buy_shares")
    @patch("agent_executor.broadcast_status")
    @patch("agent_executor.ToolTracker")
    @patch("agent_executor.Runner")
    async def test_execute_cycle_success_with_buy(
        self,
        mock_runner_class,
        mock_tracker_class,
        mock_broadcast,
        mock_buy,
        mock_get_recent_activity,
        mock_end_run,
        mock_start_run,
        mock_get_holdings,
        mock_get_balance,
        mock_get_account,
        mock_initialize,
        sample_agent_id,
        sample_agent_name,
        sample_strategy,
        sample_balance,
        sample_holdings,
        sample_recent_activity,
        sample_decision,
    ):
        """Test full execution cycle with BUY decision."""
        # Setup mocks
        mock_initialize.return_value = None
        mock_get_account.return_value = "Account report"
        mock_get_balance.return_value = sample_balance
        mock_get_holdings.return_value = sample_holdings
        mock_start_run.return_value = 123
        mock_get_recent_activity.return_value = sample_recent_activity
        mock_buy.return_value = None
        mock_end_run.return_value = None

        # Mock tracker
        mock_tracker_instance = MagicMock()
        mock_tracker_class.return_value = mock_tracker_instance

        # Mock agent result
        mock_result = MagicMock()
        final_msg = MagicMock()
        final_msg.role = "assistant"
        final_msg.content = "Decided to buy NVDA"
        mock_result.messages = [final_msg]
        mock_runner_class.run = AsyncMock(return_value=mock_result)

        # Create mock tool factory and message builder
        mock_tool_factory = MagicMock()
        mock_agent = MagicMock()
        mock_tool_factory.create_agent = AsyncMock(return_value=mock_agent)

        mock_message_builder = MagicMock()
        mock_message_builder.build_message.return_value = "Execute trading cycle"

        # Create executor and store decision manually (simulating decide_action call)
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)
        executor.store_decision(
            action="BUY",
            symbol="NVDA",
            quantity=50,
            rationale="AI growth",
            full_reasoning="Strong fundamentals",
            research_sources=json.dumps({"summary": "NVDA analysis", "sources": []}),
            historical_context=json.dumps({"summary": "No prior trades", "insights": []}),
        )

        # Execute full cycle
        result = await executor.execute_cycle(
            message_builder=mock_message_builder,
            tool_factory=mock_tool_factory,
            force_trade=False,
        )

        # Verify result
        assert result["decision"]["action"] == "BUY"
        assert result["trade_count"] == 1
        assert result["run_id"] == 123

        # Verify all phases executed
        mock_initialize.assert_called_once()
        mock_get_recent_activity.assert_called_once()
        mock_tool_factory.create_agent.assert_called_once()
        mock_runner_class.run.assert_called_once()
        mock_buy.assert_called_once()
        mock_end_run.assert_called_once()

        # Verify cleanup
        assert executor.current_run_id is None
        assert executor.trade_count == 0
        assert executor.last_decision is None
        assert executor.tracker is None

    @patch("agent_executor.initialize_agent")
    @patch("agent_executor.start_run")
    @patch("agent_executor.mark_run_as_error")
    @patch("agent_executor.broadcast_status")
    @patch("agent_executor._get_balance_raw")
    @patch("agent_executor._get_holdings_raw")
    @patch("agent_executor.get_account_report")
    @patch("agent_executor.ToolTracker")
    async def test_execute_cycle_handles_error(
        self,
        mock_tracker_class,
        mock_get_account,
        mock_get_holdings,
        mock_get_balance,
        mock_broadcast,
        mock_mark_error,
        mock_start_run,
        mock_initialize,
        sample_agent_id,
        sample_agent_name,
        sample_strategy,
    ):
        """Test full cycle handles errors and cleans up."""
        # Setup mocks
        mock_initialize.return_value = None
        mock_get_account.return_value = "Account report"
        mock_get_balance.return_value = 100000.0
        mock_get_holdings.return_value = []
        mock_start_run.return_value = 123
        mock_mark_error.return_value = None

        # Mock tracker
        mock_tracker_instance = MagicMock()
        mock_tracker_class.return_value = mock_tracker_instance

        # Create mock tool factory that raises error
        mock_tool_factory = MagicMock()
        mock_tool_factory.create_agent = AsyncMock(
            side_effect=Exception("Tool creation failed")
        )

        mock_message_builder = MagicMock()

        # Create executor
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)

        # Execute cycle - should raise error
        with pytest.raises(Exception) as exc_info:
            await executor.execute_cycle(
                message_builder=mock_message_builder,
                tool_factory=mock_tool_factory,
                force_trade=False,
            )

        assert "Tool creation failed" in str(exc_info.value)

        # Verify error handling
        mock_mark_error.assert_called_once_with(123, "Tool creation failed")

        # Verify cleanup still happened
        assert executor.current_run_id is None
        assert executor.trade_count == 0
        assert executor.last_decision is None
        assert executor.tracker is None


@pytest.mark.asyncio
class TestAgentExecutorHelperMethods:
    """Test helper methods."""

    def test_extract_urls_from_source_citations(
        self, sample_agent_id, sample_agent_name, sample_strategy
    ):
        """Test URL extraction from SOURCE citations."""
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)

        text = """Analysis shows [SOURCE: TechNews](https://example.com/tech)
        and [SOURCE: MarketWatch](https://example.com/market) support this."""

        sources = executor._extract_urls_from_text(text)

        assert len(sources) == 2
        assert sources[0]["title"] == "TechNews"
        assert sources[0]["url"] == "https://example.com/tech"
        assert sources[1]["title"] == "MarketWatch"
        assert sources[1]["url"] == "https://example.com/market"

    def test_extract_urls_fallback_to_markdown_links(
        self, sample_agent_id, sample_agent_name, sample_strategy
    ):
        """Test URL extraction falls back to markdown links."""
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)

        text = """Check out [this article](https://example.com/article) for more."""

        sources = executor._extract_urls_from_text(text)

        assert len(sources) == 1
        assert sources[0]["title"] == "this article"
        assert sources[0]["url"] == "https://example.com/article"

    def test_parse_research_summary(
        self, sample_agent_id, sample_agent_name, sample_strategy
    ):
        """Test research summary parsing."""
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)

        research_text = """NVDA shows strong AI growth with new chips.
        [SOURCE: TechNews](https://example.com/nvda)
        Market conditions favor continued expansion."""

        sources = [{"title": "TechNews", "url": "https://example.com/nvda"}]

        summary = executor._parse_research_summary(research_text, sources)

        assert "NVDA" in summary
        assert "(Cited 1 source)" in summary
        assert "[SOURCE:" not in summary  # Citations stripped

    def test_store_decision(
        self, sample_agent_id, sample_agent_name, sample_strategy
    ):
        """Test decision storage."""
        executor = AgentExecutor(sample_agent_id, sample_agent_name, sample_strategy)

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
        assert executor.last_decision["action"] == "BUY"
        assert executor.last_decision["symbol"] == "AAPL"
        assert executor.last_decision["quantity"] == 100
        assert executor.last_decision["researchSources"] == '{"summary": "test"}'
