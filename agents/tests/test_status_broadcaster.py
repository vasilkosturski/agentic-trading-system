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
