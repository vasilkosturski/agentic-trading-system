"""Tests for status_broadcaster.broadcast_status_async exception handling.

Verifies that:
  * BackendAPIError (HTTP status / timeout / network — what BackendClient maps
    everything HTTP-level into) is logged at WARN and swallowed so status
    broadcasts never fail trading logic.
  * Non-HTTP exceptions (e.g. RuntimeError, asyncio.CancelledError) propagate,
    so we don't accidentally hide programming errors or break cooperative
    cancellation.
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

import backend.status_broadcaster as status_broadcaster
from infra.exceptions import BackendAPIError


def _patch_backend_client(mocker, request_mock):
    """Patch get_backend_client() to return a stub whose .request is request_mock."""
    client = MagicMock()
    client.request = request_mock
    return mocker.patch.object(status_broadcaster, "get_backend_client", return_value=client)


@pytest.mark.asyncio
async def test_backend_api_error_is_logged_and_swallowed(mocker, caplog):
    """A BackendAPIError raised during POST is logged at WARN and does not propagate."""
    request_mock = AsyncMock(
        side_effect=BackendAPIError("HTTP 403: Access Denied", status_code=403)
    )
    _patch_backend_client(mocker, request_mock)

    with caplog.at_level(logging.WARNING, logger=status_broadcaster.logger.name):
        # Must not raise — broadcasts never fail trading logic for HTTP-level issues.
        await status_broadcaster.broadcast_status_async(
            agent_id=1,
            agent_name="Warren",
            phase="RESEARCHING",
            message="looking around",
            progress=10,
        )

    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warning_records, "expected a WARN log for the BackendAPIError"
    assert any("Warren" in r.getMessage() for r in warning_records)


@pytest.mark.asyncio
async def test_runtime_error_propagates(mocker):
    """A non-HTTP RuntimeError must propagate — programming bugs should not be hidden."""
    request_mock = AsyncMock(side_effect=RuntimeError("genuine bug"))
    _patch_backend_client(mocker, request_mock)

    with pytest.raises(RuntimeError, match="genuine bug"):
        await status_broadcaster.broadcast_status_async(
            agent_id=1,
            agent_name="Warren",
            phase="RESEARCHING",
            message="...",
            progress=30,
        )


@pytest.mark.asyncio
async def test_cancelled_error_propagates(mocker):
    """asyncio.CancelledError must propagate so cooperative cancellation works."""
    request_mock = AsyncMock(side_effect=asyncio.CancelledError())
    _patch_backend_client(mocker, request_mock)

    with pytest.raises(asyncio.CancelledError):
        await status_broadcaster.broadcast_status_async(
            agent_id=1,
            agent_name="Warren",
            phase="RESEARCHING",
            message="...",
            progress=40,
        )


@pytest.mark.asyncio
async def test_successful_broadcast_emits_no_warning(mocker, caplog):
    """A successful BackendClient.request returns normally with no WARN logs."""
    request_mock = AsyncMock(return_value=MagicMock())
    _patch_backend_client(mocker, request_mock)

    with caplog.at_level(logging.WARNING, logger=status_broadcaster.logger.name):
        await status_broadcaster.broadcast_status_async(
            agent_id=1,
            agent_name="Warren",
            phase="COMPLETED",
            message="done",
            progress=100,
            outcome="ok",
        )

    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warning_records == []
    request_mock.assert_awaited_once()
    call_kwargs = request_mock.await_args.kwargs
    assert call_kwargs["json_data"]["agentName"] == "Warren"
    assert call_kwargs["json_data"]["phase"] == "COMPLETED"


def test_broadcast_status_sync_schedules_task_on_running_loop(mocker):
    """The fire-and-forget ``broadcast_status`` wrapper must call
    ``loop.create_task`` so the HTTP POST happens out-of-band.

    We patch ``asyncio.get_running_loop`` at the call site so we hand the
    function a fake loop whose ``create_task`` we can assert on. The fake
    loop's ``create_task`` immediately ``.close()`` s the coroutine so no
    unawaited-coroutine warnings leak into other tests.
    """
    fake_loop = MagicMock()
    captured: dict = {}

    def fake_create_task(coro, *args, **kwargs):
        captured["coro"] = coro
        # Close the coroutine so we don't leak un-awaited coros.
        coro.close()
        return MagicMock()

    fake_loop.create_task.side_effect = fake_create_task

    # Patch the symbol the way the module accesses it: status_broadcaster
    # imports `asyncio` and calls ``asyncio.get_running_loop()``.
    mocker.patch.object(status_broadcaster.asyncio, "get_running_loop", return_value=fake_loop)

    status_broadcaster.broadcast_status(
        agent_id=42,
        agent_name="Cathie",
        phase="DECIDING",
        message="thinking",
        progress=70,
    )

    fake_loop.create_task.assert_called_once()
    assert captured.get("coro") is not None, "expected the async coro to be passed to create_task"


def test_broadcast_status_outside_event_loop_does_not_raise(caplog):
    """Called from a thread with no running loop, ``broadcast_status`` must
    swallow the ``RuntimeError`` (debug-log) rather than crashing the caller.

    Implementation note: we drive the function from a fresh OS thread so the
    surrounding pytest-asyncio fixture's event loop (when ``asyncio_mode=auto``)
    can't be observed via ``asyncio.get_running_loop()``. That makes the
    "no running loop" branch deterministic regardless of how this test file
    is configured at the module level.
    """
    import threading

    errors: list[BaseException] = []

    def call_from_thread() -> None:
        try:
            with caplog.at_level(logging.DEBUG, logger=status_broadcaster.logger.name):
                status_broadcaster.broadcast_status(
                    agent_id=1,
                    agent_name="Warren",
                    phase="INITIALIZING",
                    message="early",
                    progress=0,
                )
        except BaseException as exc:  # pragma: no cover - failure path
            errors.append(exc)

    t = threading.Thread(target=call_from_thread)
    t.start()
    t.join(timeout=5)

    assert not t.is_alive(), "broadcast_status hung when called without a loop"
    assert errors == [], f"broadcast_status raised when no loop was running: {errors}"
