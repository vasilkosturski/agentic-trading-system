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
from models.run_tracking import CompleteRunData, RunPhase


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
