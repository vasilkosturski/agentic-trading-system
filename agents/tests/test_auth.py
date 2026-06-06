"""Tests for JwtAuth httpx.Auth subclass."""

from __future__ import annotations

import httpx
import pytest

from backend.auth import JwtAuth
from infra.exceptions import BackendAPIError


def _credentials():
    return ("admin", "admin-pw")


def _login_response(token: str = "jwt-1") -> httpx.Response:
    return httpx.Response(
        status_code=200,
        json={"token": token, "username": "admin"},
        headers={"content-type": "application/json"},
    )


def _ok_response() -> httpx.Response:
    return httpx.Response(
        status_code=200,
        json={"ok": True},
        headers={"content-type": "application/json"},
    )


def _unauthorized() -> httpx.Response:
    return httpx.Response(status_code=401)


class _RecordingTransport(httpx.AsyncBaseTransport):
    """Async transport that returns queued responses and snapshots requests.

    Captures a (method, url-path, Authorization-header) snapshot at the moment
    the request is dispatched. Necessary because httpx may mutate the same
    Request object's headers across retries — recording the object reference
    alone would lose the per-attempt header value.
    """

    def __init__(self, responses: list[httpx.Response]):
        self._responses = list(responses)
        self.requests: list[dict[str, str | None]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(
            {
                "method": request.method,
                "path": request.url.path,
                "authorization": request.headers.get("Authorization"),
            }
        )
        if not self._responses:
            raise AssertionError(f"No more queued responses; unexpected: {request}")
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_first_call_logs_in_and_attaches_bearer():
    transport = _RecordingTransport([_login_response("jwt-abc"), _ok_response()])
    auth = JwtAuth(login_url="http://x/api/auth/login", credentials_provider=_credentials)

    async with httpx.AsyncClient(transport=transport, auth=auth) as client:
        response = await client.get("http://x/api/agents")

    assert response.status_code == 200
    assert len(transport.requests) == 2
    assert transport.requests[0]["path"] == "/api/auth/login"
    assert transport.requests[1]["authorization"] == "Bearer jwt-abc"


@pytest.mark.asyncio
async def test_401_invalidates_cache_and_retries_once():
    transport = _RecordingTransport(
        [
            _login_response("jwt-old"),
            _unauthorized(),
            _login_response("jwt-new"),
            _ok_response(),
        ]
    )
    auth = JwtAuth(login_url="http://x/api/auth/login", credentials_provider=_credentials)

    async with httpx.AsyncClient(transport=transport, auth=auth) as client:
        response = await client.get("http://x/api/agents")

    assert response.status_code == 200
    assert len(transport.requests) == 4
    assert transport.requests[1]["authorization"] == "Bearer jwt-old"
    assert transport.requests[2]["path"] == "/api/auth/login"
    assert transport.requests[3]["authorization"] == "Bearer jwt-new"


@pytest.mark.asyncio
async def test_second_401_surfaces_to_caller():
    transport = _RecordingTransport(
        [
            _login_response("jwt-1"),
            _unauthorized(),
            _login_response("jwt-2"),
            _unauthorized(),
        ]
    )
    auth = JwtAuth(login_url="http://x/api/auth/login", credentials_provider=_credentials)

    async with httpx.AsyncClient(transport=transport, auth=auth) as client:
        response = await client.get("http://x/api/agents")

    # Second 401 is returned as-is so the caller's error handler maps it to a
    # BackendAPIError(status=401).
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_cached_across_calls():
    transport = _RecordingTransport(
        [
            _login_response("jwt-cache"),
            _ok_response(),
            _ok_response(),
        ]
    )
    auth = JwtAuth(login_url="http://x/api/auth/login", credentials_provider=_credentials)

    async with httpx.AsyncClient(transport=transport, auth=auth) as client:
        await client.get("http://x/api/a")
        await client.get("http://x/api/b")

    login_count = sum(1 for r in transport.requests if r["path"] == "/api/auth/login")
    assert login_count == 1
    assert transport.requests[1]["authorization"] == "Bearer jwt-cache"
    assert transport.requests[2]["authorization"] == "Bearer jwt-cache"


@pytest.mark.asyncio
async def test_login_failure_raises_backend_api_error():
    transport = _RecordingTransport(
        [
            httpx.Response(
                status_code=503,
                text="upstream gateway down",
            ),
        ]
    )
    auth = JwtAuth(login_url="http://x/api/auth/login", credentials_provider=_credentials)

    async with httpx.AsyncClient(transport=transport, auth=auth) as client:
        with pytest.raises(BackendAPIError) as exc_info:
            await client.get("http://x/api/agents")

    assert exc_info.value.status_code == 503


def test_credentials_provider_called_on_demand():
    calls: list[int] = []

    def provider():
        calls.append(1)
        return ("admin", "admin-pw")

    JwtAuth(login_url="http://x/api/auth/login", credentials_provider=provider)
    # Constructor does NOT eagerly call the provider — it's invoked lazily on login.
    assert calls == []
