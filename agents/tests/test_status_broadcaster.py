"""Tests for status_broadcaster.broadcast_status_async exception handling (W10).

Verifies that the outer except clause is narrowed to httpx.HTTPError so that:
  * httpx.HTTPError (including TimeoutException and HTTPStatusError) is logged
    at WARN and swallowed.
  * Non-HTTP exceptions (e.g. RuntimeError, asyncio.CancelledError) propagate,
    so we don't accidentally hide programming errors or break cooperative
    cancellation.
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import status_broadcaster


def _patch_async_client(mocker, client_mock):
    """Patch httpx.AsyncClient so `async with httpx.AsyncClient(...)` yields client_mock."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client_mock)
    cm.__aexit__ = AsyncMock(return_value=None)
    return mocker.patch.object(status_broadcaster.httpx, "AsyncClient", return_value=cm)


@pytest.mark.asyncio
async def test_http_error_is_logged_and_swallowed(mocker, caplog):
    """An httpx.HTTPError raised during POST is logged at WARN and does not propagate."""
    client = MagicMock()
    request = httpx.Request("POST", "http://localhost:8080/api/agents/status")
    client.post = AsyncMock(side_effect=httpx.ConnectError("boom", request=request))
    _patch_async_client(mocker, client)

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
    assert warning_records, "expected a WARN log for the HTTP error"
    assert any("Warren" in r.getMessage() for r in warning_records)


@pytest.mark.asyncio
async def test_timeout_exception_is_logged_and_swallowed(mocker, caplog):
    """httpx.TimeoutException (a subclass of HTTPError) is also handled by the narrow except."""
    client = MagicMock()
    client.post = AsyncMock(side_effect=httpx.ReadTimeout("slow"))
    _patch_async_client(mocker, client)

    with caplog.at_level(logging.WARNING, logger=status_broadcaster.logger.name):
        await status_broadcaster.broadcast_status_async(
            agent_id=1,
            agent_name="Warren",
            phase="RESEARCHING",
            message="...",
            progress=20,
        )

    assert any(r.levelno == logging.WARNING for r in caplog.records)


@pytest.mark.asyncio
async def test_runtime_error_propagates(mocker):
    """A non-HTTP RuntimeError must propagate — programming bugs should not be hidden."""
    client = MagicMock()
    client.post = AsyncMock(side_effect=RuntimeError("genuine bug"))
    _patch_async_client(mocker, client)

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
    client = MagicMock()
    client.post = AsyncMock(side_effect=asyncio.CancelledError())
    _patch_async_client(mocker, client)

    with pytest.raises(asyncio.CancelledError):
        await status_broadcaster.broadcast_status_async(
            agent_id=1,
            agent_name="Warren",
            phase="RESEARCHING",
            message="...",
            progress=40,
        )


# ============================================================================
# Additional retry / response-handling branches (I11)
# ============================================================================


@pytest.mark.asyncio
async def test_non_2xx_status_logs_warning_but_does_not_raise(mocker, caplog):
    """A successful HTTP exchange returning a non-2xx (e.g. 500) status must
    log at WARN and return normally — broadcasts never fail trading logic.
    """
    response = MagicMock()
    response.status_code = 500
    client = MagicMock()
    client.post = AsyncMock(return_value=response)
    _patch_async_client(mocker, client)

    with caplog.at_level(logging.WARNING, logger=status_broadcaster.logger.name):
        await status_broadcaster.broadcast_status_async(
            agent_id=1,
            agent_name="Warren",
            phase="RESEARCHING",
            message="...",
            progress=50,
        )

    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warning_records, "expected a WARN log for non-2xx status"
    assert any("500" in r.getMessage() for r in warning_records)


@pytest.mark.asyncio
async def test_204_response_treated_as_success_no_warning(mocker, caplog):
    """A 204 No Content response is the documented success path and must
    not produce any WARN log records."""
    response = MagicMock()
    response.status_code = 204
    client = MagicMock()
    client.post = AsyncMock(return_value=response)
    _patch_async_client(mocker, client)

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
    mocker.patch.object(
        status_broadcaster.asyncio, "get_running_loop", return_value=fake_loop
    )

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
            with caplog.at_level(
                logging.DEBUG, logger=status_broadcaster.logger.name
            ):
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
