"""Tests for `run_lifecycle.RunLifecycle` — the Trading Runs API + status
broadcast facade extracted from `AgentExecutor`.

All tests mock dependencies at `run_lifecycle.<symbol>` (not at
`agent_executor.<symbol>`) because the new module owns its own imports.

`pyproject.toml` sets `asyncio_mode = "auto"`, so async tests need no
explicit `@pytest.mark.asyncio` decorator.
"""

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

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def lifecycle() -> RunLifecycle:
    """A RunLifecycle with a normal (truthy) agent_id."""
    return RunLifecycle(agent_id=1, agent_name="Warren")


# ---------------------------------------------------------------------------
# Test 1: start() success path emits two broadcasts in order
# ---------------------------------------------------------------------------


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
    """start(): initialize_agent → broadcast(INITIALIZING) → create_run →
    update_phase(RESEARCHING) → broadcast(RESEARCHING) → return run_id."""
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


# ---------------------------------------------------------------------------
# Test 2: start() raises RuntimeError if agent_id is falsy
# ---------------------------------------------------------------------------


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
    """RunLifecycle constructed with agent_id=None must raise RuntimeError
    from start() — mirrors the existing _start_run guard in agent_executor."""
    lifecycle = RunLifecycle(agent_id=None, agent_name="Warren")  # type: ignore[arg-type]

    with pytest.raises(RuntimeError) as exc_info:
        await lifecycle.start()

    # Message must indicate the agent is not registered / setup.
    msg = str(exc_info.value).lower()
    assert "warren" in msg or "agent" in msg


# ---------------------------------------------------------------------------
# Test 3: transition_to_deciding emits phase update THEN broadcast
# ---------------------------------------------------------------------------


async def test_transition_to_deciding_emits_phase_update_then_broadcast(
    lifecycle: RunLifecycle,
) -> None:
    """update_phase fires before broadcast_status (call order verified)."""
    parent = MagicMock()
    parent.update_phase = AsyncMock()
    parent.broadcast_status = MagicMock()

    with (
        patch("backend.run_lifecycle.update_phase", parent.update_phase),
        patch("backend.run_lifecycle.broadcast_status", parent.broadcast_status),
    ):
        await lifecycle.transition_to_deciding(run_id=42)

    parent.update_phase.assert_awaited_once_with(42, RunPhase.DECIDING)
    parent.broadcast_status.assert_called_once_with(
        1, "Warren", PHASE_DECIDING, "Making investment decision", 70
    )

    # Verify ORDER: update_phase before broadcast_status.
    call_names = [
        call[0] for call in parent.mock_calls if call[0] in ("update_phase", "broadcast_status")
    ]
    assert call_names == ["update_phase", "broadcast_status"]


# ---------------------------------------------------------------------------
# Test 4: transition_to_trading emits phase update THEN broadcast
# ---------------------------------------------------------------------------


async def test_transition_to_trading_emits_phase_update_then_broadcast(
    lifecycle: RunLifecycle,
) -> None:
    """Same shape as transition_to_deciding but with TRADING."""
    parent = MagicMock()
    parent.update_phase = AsyncMock()
    parent.broadcast_status = MagicMock()

    with (
        patch("backend.run_lifecycle.update_phase", parent.update_phase),
        patch("backend.run_lifecycle.broadcast_status", parent.broadcast_status),
    ):
        await lifecycle.transition_to_trading(run_id=42)

    parent.update_phase.assert_awaited_once_with(42, RunPhase.TRADING)
    parent.broadcast_status.assert_called_once_with(
        1, "Warren", PHASE_TRADING, "Executing trade", 90
    )

    call_names = [
        call[0] for call in parent.mock_calls if call[0] in ("update_phase", "broadcast_status")
    ]
    assert call_names == ["update_phase", "broadcast_status"]


# ---------------------------------------------------------------------------
# Test 5: complete() calls complete_run then broadcasts COMPLETED
# ---------------------------------------------------------------------------


@patch("backend.run_lifecycle.broadcast_status")
@patch("backend.run_lifecycle.complete_run", new_callable=AsyncMock)
async def test_complete_calls_complete_run_then_broadcasts_completed(
    mock_complete_run: AsyncMock,
    mock_broadcast_status: MagicMock,
    lifecycle: RunLifecycle,
) -> None:
    """complete(): complete_run(run_id, data) then broadcast COMPLETED with
    progress=100 and outcome=outcome_message."""
    mock_data = MagicMock(spec=CompleteRunData)
    outcome = "Completed - 1 trade executed"

    await lifecycle.complete(run_id=42, data=mock_data, outcome_message=outcome)

    mock_complete_run.assert_awaited_once_with(42, mock_data)
    mock_broadcast_status.assert_called_once_with(
        1, "Warren", PHASE_COMPLETED, outcome, 100, outcome=outcome
    )


# ---------------------------------------------------------------------------
# Test 6: fail() with run_id logs, broadcasts ERROR, and updates phase to FAILED
# ---------------------------------------------------------------------------


@patch("backend.run_lifecycle.broadcast_status")
@patch("backend.run_lifecycle.update_phase", new_callable=AsyncMock)
async def test_fail_with_run_id_logs_broadcasts_error_and_updates_phase_failed(
    mock_update_phase: AsyncMock,
    mock_broadcast_status: MagicMock,
    lifecycle: RunLifecycle,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """fail() emits ERROR broadcast and marks the run FAILED — does NOT raise."""
    err = RuntimeError("boom")

    with caplog.at_level(logging.ERROR, logger="run_lifecycle"):
        # fail() returns None per its annotation; we assert it doesn't raise
        # (and assigning the result would trip mypy's func-returns-value rule).
        await lifecycle.fail(run_id=42, error=err)

    mock_broadcast_status.assert_called_once_with(
        1, "Warren", PHASE_ERROR, "Error: boom", 0, outcome="Failed: boom"
    )
    mock_update_phase.assert_awaited_once_with(42, RunPhase.FAILED, error_message="boom")

    # At least one ERROR-level log line about the cycle error must appear.
    cycle_error_logs = [
        rec for rec in caplog.records if rec.levelno == logging.ERROR and "boom" in rec.getMessage()
    ]
    assert cycle_error_logs, "expected at least one ERROR log line referencing the cycle error"


# ---------------------------------------------------------------------------
# Test 7: fail() with no run_id still broadcasts but skips update_phase
# ---------------------------------------------------------------------------


@patch("backend.run_lifecycle.broadcast_status")
@patch("backend.run_lifecycle.update_phase", new_callable=AsyncMock)
async def test_fail_with_no_run_id_broadcasts_but_skips_update_phase(
    mock_update_phase: AsyncMock,
    mock_broadcast_status: MagicMock,
    lifecycle: RunLifecycle,
) -> None:
    """When run_id is None, broadcast still happens but update_phase is NOT
    called (there is no run to mark FAILED)."""
    await lifecycle.fail(run_id=None, error=RuntimeError("pre-run failure"))

    mock_broadcast_status.assert_called_once()
    mock_update_phase.assert_not_called()


# ---------------------------------------------------------------------------
# Test 8: fail() swallows cleanup errors and does NOT raise
# ---------------------------------------------------------------------------


@patch("backend.run_lifecycle.broadcast_status")
@patch("backend.run_lifecycle.update_phase", new_callable=AsyncMock)
async def test_fail_swallows_cleanup_errors_and_does_not_raise(
    mock_update_phase: AsyncMock,
    mock_broadcast_status: MagicMock,
    lifecycle: RunLifecycle,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If update_phase itself raises during error recording, fail() must log
    and return normally — the swallowed-cleanup-error contract is load-bearing.
    """
    mock_update_phase.side_effect = RuntimeError("cleanup boom")

    with caplog.at_level(logging.ERROR, logger="run_lifecycle"):
        # Must return normally — never propagate the cleanup error.
        # (Don't assign the result; mypy's func-returns-value rule fires on
        # `result = await fn()` when fn() is annotated `-> None`.)
        await lifecycle.fail(run_id=42, error=RuntimeError("original"))

    # broadcast still happened.
    mock_broadcast_status.assert_called_once()

    # Exactly two ERROR records: one for the original cycle error and one
    # for the cleanup failure. Asserting == (not >=) catches accidental
    # double-logging regressions in fail().
    error_records = [rec for rec in caplog.records if rec.levelno == logging.ERROR]
    assert len(error_records) == 2, (
        f"expected exactly 2 ERROR log records (original + cleanup); got {len(error_records)}"
    )
    messages = " ".join(rec.getMessage() for rec in error_records)
    assert "original" in messages
    assert "cleanup boom" in messages
