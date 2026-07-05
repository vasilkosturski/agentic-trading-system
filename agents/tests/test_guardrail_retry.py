"""Tests for guardrail_retry.run_with_guardrail_retry().

All tests mock Runner.run() -- no real LLM calls.
"""

import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import tenacity
from agents.exceptions import OutputGuardrailTripwireTriggered

from ai_agents import guardrail_retry
from ai_agents.guardrail_retry import GuardrailOutcome, run_with_guardrail_retry
from logging_config import _StableJsonFormatter


@pytest.fixture(autouse=True)
def _no_retry_sleep(monkeypatch):
    """Neutralize backoff waits between retry attempts so tests stay fast."""
    monkeypatch.setattr(guardrail_retry, "_WAIT", tenacity.wait_none())


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


def _make_message_output_item(text: str):
    """Build a mock MessageOutputItem whose text-extraction returns ``text``.

    The retry helper extracts the LLM's rejected JSON output by locating the
    last MessageOutputItem in ``run_data.new_items`` and calling the SDK's
    ``ItemHelpers.text_message_output`` on it. Tests mock that helper rather
    than building a full ``ResponseOutputMessage`` so the assertion stays
    focused on the retry-loop's capture behaviour.
    """
    item = MagicMock()
    item.type = "message_output_item"
    item.to_input_item.return_value = {"role": "assistant", "content": text}
    item._failed_output_text = text  # consumed by the mocked text extractor
    return item


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRunWithGuardrailRetry:
    """Tests for run_with_guardrail_retry."""

    @patch("ai_agents.guardrail_retry.Runner")
    async def test_success_first_attempt(self, mock_runner_class):
        """Runner.run succeeds on first call -- returns first_try outcome, no retry."""
        mock_result = MagicMock()
        mock_runner_class.run = AsyncMock(return_value=mock_result)

        agent = MagicMock()
        outcome = await run_with_guardrail_retry(
            agent, "test prompt", max_attempts=3, agent_name="TestAgent"
        )

        assert isinstance(outcome, GuardrailOutcome)
        assert outcome.result is mock_result
        assert outcome.attempts_used == 1
        assert outcome.outcome == "first_try"
        assert outcome.last_issues == []
        mock_runner_class.run.assert_awaited_once_with(agent, "test prompt", max_turns=30)

    @patch("ai_agents.guardrail_retry.Runner")
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
        outcome = await run_with_guardrail_retry(
            agent, "original prompt", max_attempts=3, agent_name="TestAgent"
        )

        assert outcome.result is mock_success
        assert outcome.attempts_used == 2
        assert outcome.outcome == "recovered"
        assert outcome.last_issues == ["missing candidates"]
        assert mock_runner_class.run.await_count == 2

        second_call_input = mock_runner_class.run.call_args_list[1][0][1]
        assert isinstance(second_call_input, list)

        last_item = second_call_input[-1]
        assert last_item["role"] == "user"
        assert "missing candidates" in last_item["content"]

    @patch("ai_agents.guardrail_retry.Runner")
    async def test_max_attempts_exhausted(self, mock_runner_class):
        """All attempts raise -- re-raises the last exception."""
        exc1 = _make_guardrail_exception(output_info="error 1")
        exc2 = _make_guardrail_exception(output_info="error 2")
        exc3 = _make_guardrail_exception(output_info="error 3")

        mock_runner_class.run = AsyncMock(side_effect=[exc1, exc2, exc3])

        agent = MagicMock()
        with pytest.raises(OutputGuardrailTripwireTriggered) as exc_info:
            await run_with_guardrail_retry(agent, "test", max_attempts=3, agent_name="TestAgent")

        assert exc_info.value is exc3
        assert mock_runner_class.run.await_count == 3

    @patch("ai_agents.guardrail_retry.Runner")
    async def test_raises_when_run_data_is_none(self, mock_runner_class):
        """When the SDK raises the tripwire without run_data attached, the
        retry helper must raise a clear RuntimeError instead of an opaque
        AttributeError. This locks in the explicit guard that replaces the
        old `# type: ignore[union-attr]` markers."""
        exc = _make_guardrail_exception(
            output_info="missing candidates",
            new_items=[_make_run_item()],
        )
        exc.run_data = None  # simulate SDK leaving run_data unset

        mock_runner_class.run = AsyncMock(side_effect=exc)

        agent = MagicMock()
        with pytest.raises(RuntimeError, match="run_data"):
            await run_with_guardrail_retry(agent, "test", max_attempts=3, agent_name="TestAgent")

    @patch("ai_agents.guardrail_retry.Runner")
    async def test_non_guardrail_exception_propagates_unretried(self, mock_runner_class):
        """Exceptions other than OutputGuardrailTripwireTriggered must not be retried.

        Type-narrowing the retry filter to the guardrail tripwire means a
        ``ValueError`` (or any other unrelated exception) propagates on the
        first attempt without triggering further calls to ``Runner.run``.
        """
        unrelated = ValueError("unrelated failure")
        mock_runner_class.run = AsyncMock(side_effect=unrelated)

        agent = MagicMock()
        with pytest.raises(ValueError, match="unrelated failure"):
            await run_with_guardrail_retry(
                agent, "test prompt", max_attempts=3, agent_name="TestAgent"
            )

        assert mock_runner_class.run.await_count == 1

    @patch("ai_agents.guardrail_retry.Runner")
    async def test_recovered_outcome_carries_last_failed_issues(self, mock_runner_class):
        """A `recovered` outcome must surface the LAST failed attempt's issues."""
        exc = _make_guardrail_exception(
            output_info={"issues": ["fake_url", "empty_candidates"]},
            new_items=[_make_run_item()],
        )
        mock_success = MagicMock()
        mock_runner_class.run = AsyncMock(side_effect=[exc, mock_success])

        agent = MagicMock()
        outcome = await run_with_guardrail_retry(
            agent, "prompt", max_attempts=3, agent_name="Analyst"
        )

        assert outcome.outcome == "recovered"
        assert outcome.attempts_used == 2
        assert outcome.last_issues == ["fake_url", "empty_candidates"]

    @patch("ai_agents.guardrail_retry.Runner")
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

        second_call_input = mock_runner_class.run.call_args_list[1][0][1]
        feedback_msg = second_call_input[-1]
        assert specific_error in feedback_msg["content"]
        assert "Output validation failed" in feedback_msg["content"]


# ---------------------------------------------------------------------------
# Structured-event logging tests (V1)
# ---------------------------------------------------------------------------


class _CapturingHandler(logging.Handler):
    """Logging handler that stores LogRecords for later inspection.

    Tests use this rather than ``caplog`` because we need direct access to the
    ``LogRecord`` attributes set via ``logger.warning(..., extra={...})`` to
    verify the structured-event payload, AND because we want to format the
    records through ``_StableJsonFormatter`` to prove top-level merging.
    """

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def capture_guardrail_logs():
    """Attach a capturing handler to the guardrail_retry logger."""
    handler = _CapturingHandler()
    handler.setLevel(logging.DEBUG)
    target_logger = logging.getLogger("ai_agents.guardrail_retry")
    previous_level = target_logger.level
    target_logger.addHandler(handler)
    target_logger.setLevel(logging.DEBUG)
    try:
        yield handler
    finally:
        target_logger.removeHandler(handler)
        target_logger.setLevel(previous_level)


def _find_record(handler: _CapturingHandler, event_type: str) -> logging.LogRecord:
    for rec in handler.records:
        if getattr(rec, "event_type", None) == event_type:
            return rec
    raise AssertionError(
        f"No log record with event_type={event_type!r}; "
        f"captured={[getattr(r, 'event_type', r.getMessage()) for r in handler.records]}"
    )


@pytest.mark.asyncio
class TestStructuredGuardrailEvents:
    """Verify guardrail_retry emits structured events for Loki indexing."""

    @patch("ai_agents.guardrail_retry.Runner")
    async def test_guardrail_tripped_event_emits_structured_fields_at_top_level(
        self, mock_runner_class, capture_guardrail_logs
    ):
        """Per-failed-attempt warning carries event_type+payload as record attrs."""
        exc = _make_guardrail_exception(
            output_info={"issues": ["fake_url", "empty_candidates"]},
            new_items=[_make_run_item()],
        )
        mock_success = MagicMock()
        mock_runner_class.run = AsyncMock(side_effect=[exc, mock_success])

        agent = MagicMock()
        await run_with_guardrail_retry(
            agent,
            "research prompt",
            max_attempts=3,
            agent_name="Analyst",
            run_id=42,
        )

        rec = _find_record(capture_guardrail_logs, "guardrail_tripped")
        assert rec.levelno == logging.WARNING
        assert rec.event_type == "guardrail_tripped"
        assert rec.agent_name == "Analyst"
        assert rec.attempt == 1
        assert rec.max_attempts == 3
        assert rec.issues == ["fake_url", "empty_candidates"]
        assert rec.run_id == 42

    @patch("ai_agents.guardrail_retry.Runner")
    async def test_guardrail_resolved_event_emits_on_successful_retry(
        self, mock_runner_class, capture_guardrail_logs
    ):
        """When the loop recovers after >=2 attempts, a resolved event fires."""
        exc = _make_guardrail_exception(
            output_info={"issues": ["sentinel_price"]},
            new_items=[_make_run_item()],
        )
        mock_success = MagicMock()
        mock_runner_class.run = AsyncMock(side_effect=[exc, mock_success])

        agent = MagicMock()
        await run_with_guardrail_retry(
            agent,
            "research prompt",
            max_attempts=3,
            agent_name="Analyst",
            run_id=99,
        )

        rec = _find_record(capture_guardrail_logs, "guardrail_resolved")
        assert rec.levelno == logging.INFO
        assert rec.agent_name == "Analyst"
        # Resolved on attempt 2 (the one that succeeded).
        assert rec.attempt == 2
        assert rec.max_attempts == 3
        # Issues from the LAST failed attempt that we recovered from.
        assert rec.issues == ["sentinel_price"]
        assert rec.run_id == 99

    @patch("ai_agents.guardrail_retry.Runner")
    async def test_guardrail_resolved_does_not_emit_on_first_try_success(
        self, mock_runner_class, capture_guardrail_logs
    ):
        """No resolved event when the first attempt already succeeds."""
        mock_runner_class.run = AsyncMock(return_value=MagicMock())

        agent = MagicMock()
        await run_with_guardrail_retry(agent, "prompt", max_attempts=3, agent_name="Analyst")

        with pytest.raises(AssertionError):
            _find_record(capture_guardrail_logs, "guardrail_resolved")

    @patch("ai_agents.guardrail_retry.Runner")
    async def test_guardrail_exhausted_event_emits_after_max_attempts(
        self, mock_runner_class, capture_guardrail_logs
    ):
        """Final-failure error carries event_type=guardrail_exhausted at top level."""
        exc1 = _make_guardrail_exception(output_info={"issues": ["e1"]})
        exc2 = _make_guardrail_exception(output_info={"issues": ["e2"]})
        exc3 = _make_guardrail_exception(output_info={"issues": ["final_issue"]})

        mock_runner_class.run = AsyncMock(side_effect=[exc1, exc2, exc3])

        agent = MagicMock()
        with pytest.raises(OutputGuardrailTripwireTriggered):
            await run_with_guardrail_retry(
                agent,
                "research prompt",
                max_attempts=3,
                agent_name="Analyst",
                run_id=7,
            )

        rec = _find_record(capture_guardrail_logs, "guardrail_exhausted")
        assert rec.levelno == logging.ERROR
        assert rec.agent_name == "Analyst"
        assert rec.attempt == 3
        assert rec.max_attempts == 3
        assert rec.issues == ["final_issue"]
        assert rec.run_id == 7


# ---------------------------------------------------------------------------
# V3: failed_output capture
# ---------------------------------------------------------------------------


@pytest.fixture
def _patched_text_extractor(monkeypatch):
    """Patch the text extractor used by guardrail_retry to read mock items.

    The production code calls ``ItemHelpers.text_message_output`` on each
    ``MessageOutputItem`` to recover the LLM's rejected JSON text. In tests
    we attach the desired text to the mock as ``_failed_output_text`` and
    return it from this patched extractor — same code path, no need to
    construct real ``ResponseOutputMessage`` instances.
    """

    def _extractor(item):
        return getattr(item, "_failed_output_text", "")

    monkeypatch.setattr(guardrail_retry, "_message_output_text", _extractor)


@pytest.mark.asyncio
class TestFailedOutputCapture:
    """V3: ``GuardrailOutcome.failed_output`` carries the last rejected LLM JSON."""

    @patch("ai_agents.guardrail_retry.Runner")
    async def test_failed_output_captured_on_recovered(
        self, mock_runner_class, _patched_text_extractor
    ):
        """When the loop recovers, ``failed_output`` holds the rejected JSON dict."""
        rejected_json = {
            "summary": "Banks look hot.",
            "candidates": [{"symbol": "FAKE", "price": -1}],
            "webSources": [{"title": "n/a", "url": "http://example.invalid"}],
        }
        exc = _make_guardrail_exception(
            output_info={"issues": ["fake_url"]},
            new_items=[_make_message_output_item(json.dumps(rejected_json))],
        )
        mock_success = MagicMock()
        mock_runner_class.run = AsyncMock(side_effect=[exc, mock_success])

        agent = MagicMock()
        outcome = await run_with_guardrail_retry(
            agent, "prompt", max_attempts=3, agent_name="Analyst"
        )

        assert outcome.outcome == "recovered"
        assert outcome.failed_output == rejected_json

    @patch("ai_agents.guardrail_retry.Runner")
    async def test_failed_output_captured_on_exhausted(
        self, mock_runner_class, _patched_text_extractor
    ):
        """All attempts fail — the LAST attempt's rejected JSON is attached to the
        re-raised exception via a ``guardrail_outcome`` attribute, exposing
        ``failed_output`` for downstream persistence."""
        attempt_payloads = [
            {"summary": "v1", "candidates": []},
            {"summary": "v2", "candidates": []},
            {"summary": "v3 — final", "candidates": [{"symbol": "Z", "price": 1.0}]},
        ]
        excs = [
            _make_guardrail_exception(
                output_info={"issues": [f"e{i + 1}"]},
                new_items=[_make_message_output_item(json.dumps(payload))],
            )
            for i, payload in enumerate(attempt_payloads)
        ]
        mock_runner_class.run = AsyncMock(side_effect=excs)

        agent = MagicMock()
        with pytest.raises(OutputGuardrailTripwireTriggered) as exc_info:
            await run_with_guardrail_retry(agent, "prompt", max_attempts=3, agent_name="Analyst")

        captured: GuardrailOutcome = exc_info.value.guardrail_outcome
        assert captured.outcome == "exhausted"
        assert captured.attempts_used == 3
        assert captured.failed_output == attempt_payloads[-1]

    @patch("ai_agents.guardrail_retry.Runner")
    async def test_failed_output_none_on_first_try(self, mock_runner_class):
        """First-try success carries no rejected output."""
        mock_runner_class.run = AsyncMock(return_value=MagicMock())

        agent = MagicMock()
        outcome = await run_with_guardrail_retry(
            agent, "prompt", max_attempts=3, agent_name="Analyst"
        )

        assert outcome.outcome == "first_try"
        assert outcome.failed_output is None

    @patch("ai_agents.guardrail_retry.Runner")
    async def test_failed_output_handles_non_json_text(
        self, mock_runner_class, _patched_text_extractor
    ):
        """If the LLM emitted plain text (not JSON), capture it under ``raw_text``
        so the audit trail still shows what was rejected."""
        exc = _make_guardrail_exception(
            output_info={"issues": ["fake_url"]},
            new_items=[_make_message_output_item("not actually json")],
        )
        mock_success = MagicMock()
        mock_runner_class.run = AsyncMock(side_effect=[exc, mock_success])

        agent = MagicMock()
        outcome = await run_with_guardrail_retry(
            agent, "prompt", max_attempts=3, agent_name="Analyst"
        )

        assert outcome.failed_output == {"raw_text": "not actually json"}


def test_extra_payload_merges_into_json_envelope():
    """`_StableJsonFormatter` must merge ``extra=`` keys at TOP level of the JSON.

    If keys end up nested under ``extra`` or ``props``, Loki labels won't fire
    and downstream Grafana panels break silently.
    """
    formatter = _StableJsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
        },
    )

    captured = _CapturingHandler()
    captured.setLevel(logging.DEBUG)
    test_logger = logging.getLogger("test.formatter.merge")
    test_logger.addHandler(captured)
    test_logger.setLevel(logging.DEBUG)
    test_logger.propagate = False
    try:
        test_logger.warning(
            "guardrail_tripped",
            extra={
                "event_type": "guardrail_tripped",
                "agent_name": "Analyst",
                "attempt": 1,
                "max_attempts": 3,
                "issues": ["fake_url"],
                "run_id": 42,
            },
        )
    finally:
        test_logger.removeHandler(captured)

    assert len(captured.records) == 1
    serialized = formatter.format(captured.records[0])
    envelope = json.loads(serialized)

    assert envelope["event_type"] == "guardrail_tripped"
    assert envelope["agent_name"] == "Analyst"
    assert envelope["attempt"] == 1
    assert envelope["max_attempts"] == 3
    assert envelope["issues"] == ["fake_url"]
    assert envelope["run_id"] == 42
    # Canonical fields still present.
    assert envelope["level"] == "WARNING"
    assert envelope["logger"] == "test.formatter.merge"
    # No nesting under extra/props.
    assert "extra" not in envelope
    assert "props" not in envelope
