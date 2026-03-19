"""Tests for guardrail_retry.run_with_guardrail_retry().

All tests mock Runner.run() -- no real LLM calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.exceptions import OutputGuardrailTripwireTriggered
from guardrail_retry import run_with_guardrail_retry


# ---------------------------------------------------------------------------
# Helpers to build mock exceptions
# ---------------------------------------------------------------------------

def _make_guardrail_exception(
    output_info: str = "validation error",
    input_data: str | list = "original prompt",
    new_items: list | None = None,
) -> OutputGuardrailTripwireTriggered:
    """Build a mock OutputGuardrailTripwireTriggered with run_data."""
    # guardrail_result.output.output_info
    mock_output = MagicMock()
    mock_output.output_info = output_info

    mock_guardrail_result = MagicMock()
    mock_guardrail_result.output = mock_output

    exc = OutputGuardrailTripwireTriggered.__new__(OutputGuardrailTripwireTriggered)
    exc.guardrail_result = mock_guardrail_result

    # run_data (set by SDK on AgentsException base class)
    mock_run_data = MagicMock()
    mock_run_data.input = input_data
    mock_run_data.new_items = new_items if new_items is not None else []
    exc.run_data = mock_run_data

    return exc


def _make_run_item(item_type: str = "message_output_item"):
    """Build a mock RunItem with .type and .to_input_item()."""
    item = MagicMock()
    item.type = item_type
    item.to_input_item.return_value = {"role": "assistant", "content": "mock"}
    return item


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestRunWithGuardrailRetry:
    """Tests for run_with_guardrail_retry."""

    @patch("guardrail_retry.Runner")
    async def test_success_first_attempt(self, mock_runner_class):
        """Runner.run succeeds on first call -- returns result, no retry."""
        mock_result = MagicMock()
        mock_runner_class.run = AsyncMock(return_value=mock_result)

        agent = MagicMock()
        result = await run_with_guardrail_retry(
            agent, "test prompt", max_attempts=3, agent_name="TestAgent"
        )

        assert result is mock_result
        mock_runner_class.run.assert_awaited_once_with(
            agent, "test prompt", max_turns=30
        )

    @patch("guardrail_retry.Runner")
    async def test_retry_on_guardrail_trip(self, mock_runner_class):
        """First call raises OutputGuardrailTripwireTriggered, second succeeds."""
        exc = _make_guardrail_exception(
            output_info="missing candidates",
            input_data="original prompt",
            new_items=[_make_run_item("message_output_item")],
        )
        mock_success = MagicMock()
        mock_runner_class.run = AsyncMock(side_effect=[exc, mock_success])

        agent = MagicMock()
        result = await run_with_guardrail_retry(
            agent, "original prompt", max_attempts=3, agent_name="TestAgent"
        )

        assert result is mock_success
        assert mock_runner_class.run.await_count == 2

        # Second call should receive reconstructed input list (not the original string)
        second_call_input = mock_runner_class.run.call_args_list[1][0][1]
        assert isinstance(second_call_input, list)

        # The last item should be the error feedback message
        last_item = second_call_input[-1]
        assert last_item["role"] == "user"
        assert "missing candidates" in last_item["content"]

    @patch("guardrail_retry.Runner")
    async def test_max_attempts_exhausted(self, mock_runner_class):
        """All attempts raise -- re-raises the last exception."""
        exc1 = _make_guardrail_exception(output_info="error 1")
        exc2 = _make_guardrail_exception(output_info="error 2")
        exc3 = _make_guardrail_exception(output_info="error 3")

        mock_runner_class.run = AsyncMock(side_effect=[exc1, exc2, exc3])

        agent = MagicMock()
        with pytest.raises(OutputGuardrailTripwireTriggered) as exc_info:
            await run_with_guardrail_retry(
                agent, "test", max_attempts=3, agent_name="TestAgent"
            )

        # The raised exception should be the last one (exc3)
        assert exc_info.value is exc3
        assert mock_runner_class.run.await_count == 3

    @patch("guardrail_retry.Runner")
    async def test_error_info_in_feedback(self, mock_runner_class):
        """Verify output_info from guardrail appears in retry feedback message."""
        specific_error = "Candidates list must not be empty and all symbols must be uppercase"
        exc = _make_guardrail_exception(
            output_info=specific_error,
            input_data="research prompt",
            new_items=[_make_run_item()],
        )
        mock_success = MagicMock()
        mock_runner_class.run = AsyncMock(side_effect=[exc, mock_success])

        agent = MagicMock()
        await run_with_guardrail_retry(
            agent, "research prompt", max_attempts=3, agent_name="Analyst"
        )

        # Inspect the input to the second Runner.run call
        second_call_input = mock_runner_class.run.call_args_list[1][0][1]
        feedback_msg = second_call_input[-1]
        assert specific_error in feedback_msg["content"]
        assert "Output validation failed" in feedback_msg["content"]

    @patch("guardrail_retry.Runner")
    async def test_tool_approval_items_skipped(self, mock_runner_class):
        """ToolApprovalItems in new_items are skipped during reconstruction."""
        normal_item = _make_run_item("message_output_item")
        approval_item = _make_run_item("tool_approval_item")

        exc = _make_guardrail_exception(
            output_info="bad output",
            input_data="prompt",
            new_items=[normal_item, approval_item],
        )
        mock_success = MagicMock()
        mock_runner_class.run = AsyncMock(side_effect=[exc, mock_success])

        agent = MagicMock()
        await run_with_guardrail_retry(
            agent, "prompt", max_attempts=3, agent_name="Test"
        )

        # normal_item.to_input_item() should have been called
        normal_item.to_input_item.assert_called_once()
        # approval_item.to_input_item() should NOT have been called
        approval_item.to_input_item.assert_not_called()

    @patch("guardrail_retry.Runner")
    async def test_single_attempt_raises_immediately(self, mock_runner_class):
        """With max_attempts=1, first guardrail trip raises immediately."""
        exc = _make_guardrail_exception(output_info="bad")
        mock_runner_class.run = AsyncMock(side_effect=exc)

        agent = MagicMock()
        with pytest.raises(OutputGuardrailTripwireTriggered):
            await run_with_guardrail_retry(
                agent, "test", max_attempts=1, agent_name="Test"
            )

        mock_runner_class.run.assert_awaited_once()

    @patch("guardrail_retry.Runner")
    async def test_max_turns_passed_through(self, mock_runner_class):
        """Verify max_turns parameter is forwarded to Runner.run."""
        mock_result = MagicMock()
        mock_runner_class.run = AsyncMock(return_value=mock_result)

        agent = MagicMock()
        await run_with_guardrail_retry(
            agent, "test", max_attempts=2, max_turns=50, agent_name="Test"
        )

        mock_runner_class.run.assert_awaited_once_with(agent, "test", max_turns=50)
