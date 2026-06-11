import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.run_lifecycle import RunLifecycle
from backend.status_broadcaster import (
    PHASE_COMPLETED,
    PHASE_DECIDING,
    PHASE_ERROR,
    PHASE_INITIALIZING,
    PHASE_RESEARCHING,
    PHASE_TRADING,
)
from infra.exceptions import BackendAPIError
from models.run_tracking import (
    CompleteRunData,
    DecisionPhaseData,
    ResearchPhaseData,
    RunPhase,
    TradeDecision,
)


@pytest.fixture
def lifecycle() -> RunLifecycle:
    return RunLifecycle(agent_id=1, agent_name="Warren")


@patch("backend.run_lifecycle.broadcast_status")
@patch("backend.run_lifecycle.update_phase", new_callable=AsyncMock)
@patch("backend.run_lifecycle.create_run", new_callable=AsyncMock)
@patch("backend.run_lifecycle.initialize_agent", new_callable=AsyncMock)
async def test_start_initializes_agent_creates_run_and_emits_two_broadcasts(
    mock_initialize_agent: AsyncMock,
    mock_create_run: AsyncMock,
    mock_update_phase: AsyncMock,
    mock_broadcast_status: MagicMock,
    lifecycle: RunLifecycle,
) -> None:
    mock_create_run.return_value = 999

    run_id = await lifecycle.start()

    assert run_id == 999

    mock_initialize_agent.assert_awaited_once_with("Warren")
    mock_create_run.assert_awaited_once_with(1)
    mock_update_phase.assert_awaited_once_with(999, RunPhase.RESEARCHING)

    assert mock_broadcast_status.call_count == 2
    first_call_args = mock_broadcast_status.call_args_list[0].args
    second_call_args = mock_broadcast_status.call_args_list[1].args
    assert first_call_args == (1, "Warren", PHASE_INITIALIZING, "Starting trading cycle", 0)
    assert second_call_args == (1, "Warren", PHASE_RESEARCHING, "Researching market", 20)


@patch("backend.run_lifecycle.broadcast_status")
@patch("backend.run_lifecycle.update_phase", new_callable=AsyncMock)
@patch("backend.run_lifecycle.create_run", new_callable=AsyncMock)
@patch("backend.run_lifecycle.initialize_agent", new_callable=AsyncMock)
async def test_start_raises_runtime_error_if_agent_id_falsy(
    mock_initialize_agent: AsyncMock,
    mock_create_run: AsyncMock,
    mock_update_phase: AsyncMock,
    mock_broadcast_status: MagicMock,
) -> None:
    lifecycle = RunLifecycle(agent_id=None, agent_name="Warren")  # type: ignore[arg-type]

    with pytest.raises(RuntimeError) as exc_info:
        await lifecycle.start()

    msg = str(exc_info.value).lower()
    assert "warren" in msg or "agent" in msg


@pytest.mark.parametrize(
    "transition_method, run_phase, broadcast_phase, message, progress",
    [
        (
            "transition_to_deciding",
            RunPhase.DECIDING,
            PHASE_DECIDING,
            "Making investment decision",
            70,
        ),
        ("transition_to_trading", RunPhase.TRADING, PHASE_TRADING, "Executing trade", 90),
    ],
)
async def test_transition_emits_phase_update_then_broadcast(
    lifecycle: RunLifecycle,
    transition_method: str,
    run_phase: RunPhase,
    broadcast_phase: str,
    message: str,
    progress: int,
) -> None:
    parent = MagicMock()
    parent.update_phase = AsyncMock()
    parent.broadcast_status = MagicMock()

    with (
        patch("backend.run_lifecycle.update_phase", parent.update_phase),
        patch("backend.run_lifecycle.broadcast_status", parent.broadcast_status),
    ):
        await getattr(lifecycle, transition_method)(run_id=42)

    parent.update_phase.assert_awaited_once_with(42, run_phase)
    parent.broadcast_status.assert_called_once_with(1, "Warren", broadcast_phase, message, progress)

    call_names = [
        call[0] for call in parent.mock_calls if call[0] in ("update_phase", "broadcast_status")
    ]
    assert call_names == ["update_phase", "broadcast_status"]


@patch("backend.run_lifecycle.broadcast_status")
@patch("backend.run_lifecycle.complete_run", new_callable=AsyncMock)
async def test_complete_calls_complete_run_then_broadcasts_completed(
    mock_complete_run: AsyncMock,
    mock_broadcast_status: MagicMock,
    lifecycle: RunLifecycle,
) -> None:
    mock_data = MagicMock(spec=CompleteRunData)
    outcome = "Completed - 1 trade executed"

    await lifecycle.complete(run_id=42, data=mock_data, outcome_message=outcome)

    mock_complete_run.assert_awaited_once_with(42, mock_data)
    mock_broadcast_status.assert_called_once_with(
        1, "Warren", PHASE_COMPLETED, outcome, 100, outcome=outcome
    )


@patch("backend.run_lifecycle.broadcast_status")
@patch("backend.run_lifecycle.update_phase", new_callable=AsyncMock)
async def test_fail_with_run_id_logs_broadcasts_error_and_updates_phase_failed(
    mock_update_phase: AsyncMock,
    mock_broadcast_status: MagicMock,
    lifecycle: RunLifecycle,
    caplog: pytest.LogCaptureFixture,
) -> None:
    err = RuntimeError("boom")

    with caplog.at_level(logging.ERROR, logger="run_lifecycle"):
        await lifecycle.fail(run_id=42, error=err)

    mock_broadcast_status.assert_called_once_with(
        1, "Warren", PHASE_ERROR, "Error: boom", 0, outcome="Failed: boom"
    )
    mock_update_phase.assert_awaited_once_with(42, RunPhase.FAILED, error_message="boom")

    cycle_error_logs = [
        rec for rec in caplog.records if rec.levelno == logging.ERROR and "boom" in rec.getMessage()
    ]
    assert cycle_error_logs, "expected at least one ERROR log line referencing the cycle error"


@patch("backend.run_lifecycle.broadcast_status")
@patch("backend.run_lifecycle.update_phase", new_callable=AsyncMock)
async def test_fail_with_no_run_id_broadcasts_but_skips_update_phase(
    mock_update_phase: AsyncMock,
    mock_broadcast_status: MagicMock,
    lifecycle: RunLifecycle,
) -> None:
    await lifecycle.fail(run_id=None, error=RuntimeError("pre-run failure"))

    mock_broadcast_status.assert_called_once()
    mock_update_phase.assert_not_called()


@pytest.mark.parametrize(
    "outcome, issues, failed_output",
    [
        ("first_try", None, None),
        ("recovered", ["fake_url"], None),
        ("exhausted", ["timeout"], {"summary": "bad"}),
    ],
)
def test_complete_run_payload_serializes_guardrail_outcome_fields(outcome, issues, failed_output):
    """`CompleteRunData.to_json_dict()` must round-trip every guardrail outcome shape.

    Covers the full Literal range (first_try / recovered / exhausted) with the
    matching issues + failed_output payloads each carries in production.
    """
    research = ResearchPhaseData(
        guardrailAttempts=2 if outcome != "first_try" else 1,
        guardrailIssues=issues,
        guardrailOutcome=outcome,
        guardrailFailedOutput=failed_output,
    )
    decision = DecisionPhaseData(
        decision=TradeDecision.BUY if outcome != "first_try" else TradeDecision.HOLD,
        symbol="JPM" if outcome != "first_try" else None,
        quantity=5 if outcome != "first_try" else None,
        guardrailAttempts=2 if outcome != "first_try" else 1,
        guardrailIssues=issues,
        guardrailOutcome=outcome,
        guardrailFailedOutput=failed_output,
    )
    payload = CompleteRunData(research=research, decision=decision).to_json_dict()

    # ``to_json_dict`` uses ``exclude_none=True`` so None-valued fields are
    # dropped from the wire payload. Assert presence-or-absence per outcome.
    assert payload["research"]["guardrailOutcome"] == outcome
    assert payload["research"].get("guardrailIssues") == issues
    assert payload["research"].get("guardrailFailedOutput") == failed_output
    assert payload["decision"]["guardrailOutcome"] == outcome
    assert payload["decision"].get("guardrailIssues") == issues
    assert payload["decision"].get("guardrailFailedOutput") == failed_output


@patch("backend.run_lifecycle.broadcast_status")
@patch("backend.run_lifecycle.update_phase", new_callable=AsyncMock)
async def test_fail_swallows_cleanup_errors_and_does_not_raise(
    mock_update_phase: AsyncMock,
    mock_broadcast_status: MagicMock,
    lifecycle: RunLifecycle,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_update_phase.side_effect = RuntimeError("cleanup boom")

    with caplog.at_level(logging.ERROR, logger="run_lifecycle"):
        await lifecycle.fail(run_id=42, error=RuntimeError("original"))

    mock_broadcast_status.assert_called_once()

    # Asserting == (not >=) catches accidental double-logging regressions in
    # fail(): exactly one record for the original error and one for cleanup.
    error_records = [rec for rec in caplog.records if rec.levelno == logging.ERROR]
    assert (
        len(error_records) == 2
    ), f"expected exactly 2 ERROR log records (original + cleanup); got {len(error_records)}"
    messages = " ".join(rec.getMessage() for rec in error_records)
    assert "original" in messages
    assert "cleanup boom" in messages


@patch("backend.run_lifecycle.record_phase_failure", new_callable=AsyncMock)
async def test_record_phase_failure_delegates_to_run_tracking(
    mock_record_phase_failure: AsyncMock,
    lifecycle: RunLifecycle,
) -> None:
    """``record_phase_failure`` forwards (run_id, phase_kind, outcome) to the backend wrapper."""
    outcome = MagicMock()
    outcome.outcome = "exhausted"

    await lifecycle.record_phase_failure(run_id=99, phase_kind="RESEARCH", outcome=outcome)

    mock_record_phase_failure.assert_awaited_once_with(99, "RESEARCH", outcome)


@patch("backend.run_lifecycle.record_phase_failure", new_callable=AsyncMock)
async def test_record_phase_failure_swallows_backend_errors(
    mock_record_phase_failure: AsyncMock,
    lifecycle: RunLifecycle,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Best-effort contract: backend write failure is logged, never raised.

    The phase-boundary catch sits IN a failure path — the original
    ``OutputGuardrailTripwireTriggered`` must still re-raise unobstructed so
    the orchestrator's FAILED pathway runs. Mirrors ``fail()``'s contract.
    """
    mock_record_phase_failure.side_effect = BackendAPIError("backend 500", status_code=500)
    outcome = MagicMock()

    with caplog.at_level(logging.ERROR, logger="run_lifecycle"):
        await lifecycle.record_phase_failure(run_id=42, phase_kind="DECISION", outcome=outcome)

    error_records = [rec for rec in caplog.records if rec.levelno == logging.ERROR]
    assert error_records, "expected an ERROR log when backend write fails"
    assert any("backend 500" in rec.getMessage() for rec in error_records)


@patch("backend.run_lifecycle.record_phase_failure", new_callable=AsyncMock)
async def test_record_phase_failure_propagates_programming_errors(
    mock_record_phase_failure: AsyncMock,
    lifecycle: RunLifecycle,
) -> None:
    """Programming errors (AssertionError) must fail-fast, not be swallowed.

    The best-effort catch is narrowed to the realistic backend-write failure
    surface (BackendAPIError, httpx.HTTPError, ValueError). Anything else —
    including AssertionError from an upstream assert — must propagate so the
    bug surfaces instead of being logged as a misleading "backend write failure".
    """
    mock_record_phase_failure.side_effect = AssertionError("upstream invariant broken")
    outcome = MagicMock()

    with pytest.raises(AssertionError, match="upstream invariant broken"):
        await lifecycle.record_phase_failure(run_id=42, phase_kind="DECISION", outcome=outcome)


@patch("backend.run_lifecycle.record_phase_failure", new_callable=AsyncMock)
async def test_record_phase_failure_propagates_cancelled_error(
    mock_record_phase_failure: AsyncMock,
    lifecycle: RunLifecycle,
) -> None:
    """``asyncio.CancelledError`` must propagate so cooperative shutdown works.

    On Python 3.11+, ``CancelledError`` is a ``BaseException`` (so the prior
    ``except Exception`` already let it through). Narrowing the catch keeps
    that property explicit — a regression that re-broadens the catch to
    ``Exception`` or ``BaseException`` would silently break task cancellation.
    """
    mock_record_phase_failure.side_effect = asyncio.CancelledError()
    outcome = MagicMock()

    with pytest.raises(asyncio.CancelledError):
        await lifecycle.record_phase_failure(run_id=42, phase_kind="DECISION", outcome=outcome)
