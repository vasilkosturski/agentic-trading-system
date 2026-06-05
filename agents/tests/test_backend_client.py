"""Tests for backend_client.py - HTTP client error handling.

Tests focus on ensuring the HTTP client properly handles error responses
and enforces JSON content negotiation via Accept headers.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import backend.client as backend_client_module
from backend.client import BackendClient
from infra.exceptions import BackendAPIError
from models import TradeResult
from models.api_responses import AccountReport


class TestBackendClientHttp2:
    """Verify the lazily-owned httpx.AsyncClient is constructed with HTTP/2 enabled."""

    def test_owned_client_constructed_with_http2_enabled(self):
        """The production-path AsyncClient must be created with http2=True.

        Rationale: backend runs on Traefik 2.x which supports HTTP/2; enabling
        multiplexing lets concurrent tool calls share a single TCP connection.
        """
        captured_kwargs: dict = {}
        real_async_client_cls = httpx.AsyncClient

        def fake_async_client(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return MagicMock(spec=real_async_client_cls, is_closed=False)

        client = BackendClient()
        with patch("backend.client.httpx.AsyncClient", side_effect=fake_async_client):
            client._get_client()

        assert captured_kwargs.get("http2") is True, (
            f"Expected http2=True in AsyncClient kwargs, got: {captured_kwargs}"
        )

    def test_owned_client_uses_granular_httpx_timeout(self):
        """The AsyncClient must be constructed with a granular httpx.Timeout.

        Phase-granular timeouts let connect failures fail fast while still
        allowing longer reads for the backend's heavier endpoints. We require
        the four explicit components: connect=5.0, read=15.0, write=10.0,
        pool=5.0.
        """
        captured_kwargs: dict = {}
        real_async_client_cls = httpx.AsyncClient

        def fake_async_client(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return MagicMock(spec=real_async_client_cls, is_closed=False)

        client = BackendClient()
        with patch("backend.client.httpx.AsyncClient", side_effect=fake_async_client):
            client._get_client()

        timeout = captured_kwargs.get("timeout")
        assert isinstance(timeout, httpx.Timeout), (
            f"Expected httpx.Timeout instance, got: {type(timeout).__name__}"
        )
        assert timeout.connect == 5.0, f"connect timeout: {timeout.connect}"
        assert timeout.read == 15.0, f"read timeout: {timeout.read}"
        assert timeout.write == 10.0, f"write timeout: {timeout.write}"
        assert timeout.pool == 5.0, f"pool timeout: {timeout.pool}"


class TestBackendClientErrorHandling:
    """Test suite for backend client error response handling."""

    @pytest.mark.asyncio
    async def test_json_error_handling(self):
        """Verify JSON errors are properly extracted and raised as BackendAPIError."""
        json_error_body = {
            "type": "https://trading.example.com/errors/resource-not-found",
            "title": "Resource Not Found",
            "status": 404,
            "detail": "Symbol not found: INVALID",
            "instance": "/api/market/INVALID",
        }

        mock_json_response = httpx.Response(
            status_code=404, json=json_error_body, headers={"content-type": "application/json"}
        )

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.request.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=httpx.Request("GET", "http://test.com/api/market/INVALID"),
            response=mock_json_response,
        )

        client = BackendClient(client=mock_async_client)

        with pytest.raises(BackendAPIError) as exc_info:
            await client._request("GET", "http://test.com/api/market/INVALID")

        error = exc_info.value
        error_str = str(error)
        assert "<!doctype" not in error_str.lower()
        assert "404" in error_str or "not found" in error_str.lower()


class TestPydanticParseUsesModelValidateJson:
    """I6 — Pydantic parse sites must use ``Model.model_validate_json(response.text)``.

    These tests construct ``httpx.Response`` objects whose ``.json()`` accessor
    is sabotaged via a patch (raises ``AssertionError``).  Only the ``.text``
    accessor returns a usable JSON payload.  Any parse site still using
    ``Model.model_validate(response.json())`` would trigger the sabotage and
    fail — only sites using ``response.text`` (i.e. ``model_validate_json``)
    succeed.

    Rationale: the Pydantic v2 docs recommend ``model_validate_json`` over the
    two-step ``model_validate(json.loads(...))`` because the latter performs an
    extra dict round-trip and is generally slower.  Standardizing on the
    single-call form across ``backend_client.py`` is the goal of I6.
    """

    @staticmethod
    def _text_only_response(payload_text: str) -> httpx.Response:
        """Build a Response that returns ``payload_text`` from ``.text``.

        We construct it from raw bytes so ``.text`` is well-defined, and rely
        on the test's mock-replacement of ``_request`` to deliver the response
        directly to the parse site (bypassing real HTTP).
        """
        return httpx.Response(
            status_code=200,
            content=payload_text.encode("utf-8"),
            headers={"content-type": "application/json"},
        )

    @pytest.mark.asyncio
    async def test_get_account_report_parses_via_response_text(self):
        """``get_account_report`` must validate from ``response.text``, not ``response.json()``."""
        payload_text = (
            '{"agentName":"Warren","balance":10000.0,"holdings":[],'
            '"holdingsValue":0.0,"totalPortfolioValue":10000.0,'
            '"initialBalance":10000.0,"totalProfitLoss":0.0,'
            '"profitLossPercent":0.0,"holdingsCount":0,"transactionCount":0}'
        )
        response = self._text_only_response(payload_text)

        client = BackendClient(client=AsyncMock(spec=httpx.AsyncClient))
        client._request = AsyncMock(return_value=response)  # type: ignore[method-assign]

        with patch.object(
            httpx.Response,
            "json",
            side_effect=AssertionError("parse site must use response.text"),
        ):
            report = await client.get_account_report(agent_id=1)

        assert isinstance(report, AccountReport)
        assert report.balance == 10000.0

    @pytest.mark.asyncio
    async def test_buy_shares_parses_via_response_text(self):
        """``buy_shares`` must validate from ``response.text``, not ``response.json()``."""
        payload_text = (
            '{"tradeId":42,"symbol":"AAPL","quantity":10,"price":150.0,"newBalance":98500.0}'
        )
        response = self._text_only_response(payload_text)

        client = BackendClient(client=AsyncMock(spec=httpx.AsyncClient))
        client._request = AsyncMock(return_value=response)  # type: ignore[method-assign]

        with patch.object(
            httpx.Response,
            "json",
            side_effect=AssertionError("parse site must use response.text"),
        ):
            result = await client.buy_shares(agent_id=1, symbol="AAPL", quantity=10)

        assert isinstance(result, TradeResult)
        assert result.tradeId == 42

    @pytest.mark.asyncio
    async def test_sell_shares_parses_via_response_text(self):
        """``sell_shares`` must validate from ``response.text``, not ``response.json()``."""
        payload_text = (
            '{"tradeId":43,"symbol":"AAPL","quantity":5,"price":151.0,"newBalance":99255.0}'
        )
        response = self._text_only_response(payload_text)

        client = BackendClient(client=AsyncMock(spec=httpx.AsyncClient))
        client._request = AsyncMock(return_value=response)  # type: ignore[method-assign]

        with patch.object(
            httpx.Response,
            "json",
            side_effect=AssertionError("parse site must use response.text"),
        ):
            result = await client.sell_shares(agent_id=1, symbol="AAPL", quantity=5)

        assert isinstance(result, TradeResult)
        assert result.tradeId == 43


# ---------------------------------------------------------------------------
# JWT login flow — controller-side @PreAuthorize gating requires the agents
# pod to log in as admin and attach a Bearer token on every backend call.
# ---------------------------------------------------------------------------


class _FakeHttpxClient:
    """Minimal stand-in for httpx.AsyncClient that records request calls.

    Records each call to ``request`` and returns a queued ``httpx.Response``.
    Distinguishes login posts (`/api/auth/login`) from other calls so tests
    can assert order, header injection, and 401-retry behavior independently.
    """

    def __init__(self, responses: list[httpx.Response]):
        self._responses = list(responses)
        self.calls: list[dict] = []
        self.is_closed = False

    async def request(self, method, url, *, params=None, json=None, headers=None):
        call = {
            "method": method,
            "url": url,
            "params": params,
            "json": json,
            "headers": headers or {},
        }
        self.calls.append(call)
        if not self._responses:
            raise AssertionError(f"No more queued responses; unexpected call: {call}")
        response = self._responses.pop(0)
        # ``raise_for_status`` requires a bound request; attach a synthetic one.
        response.request = httpx.Request(method, url)
        return response

    async def aclose(self):
        self.is_closed = True


def _json_response(status: int, payload: dict | None = None) -> httpx.Response:
    if payload is None:
        return httpx.Response(status_code=status)
    return httpx.Response(
        status_code=status,
        json=payload,
        headers={"content-type": "application/json"},
    )


class TestBackendClientJwtLogin:
    """JWT login + bearer-attach + 401-retry contract."""

    @pytest.fixture(autouse=True)
    def _patch_admin_creds(self, monkeypatch):
        """Make sure the BackendClient sees deterministic admin credentials."""
        monkeypatch.setattr(backend_client_module, "ADMIN_USERNAME", "admin", raising=True)
        monkeypatch.setattr(backend_client_module, "ADMIN_PASSWORD", "admin-pw", raising=True)

    @pytest.mark.asyncio
    async def test_login_happens_before_first_state_changing_call(self):
        """A POST that mutates state must be preceded by POST /api/auth/login."""
        responses = [
            _json_response(200, {"token": "jwt-abc", "username": "admin"}),
            _json_response(200, {"id": 7, "name": "Warren"}),
        ]
        fake_http = _FakeHttpxClient(responses)
        client = BackendClient(client=fake_http)

        agent_id = await client.initialize_agent("Warren", initial_balance=10000.0)

        assert agent_id == 7
        assert len(fake_http.calls) == 2, fake_http.calls
        login_call = fake_http.calls[0]
        assert login_call["method"] == "POST"
        assert login_call["url"].endswith("/api/auth/login")
        assert login_call["json"] == {"username": "admin", "password": "admin-pw"}

    @pytest.mark.asyncio
    async def test_authorization_header_attached_after_login(self):
        """Every backend call after login carries `Authorization: Bearer <jwt>`."""
        responses = [
            _json_response(200, {"token": "jwt-xyz", "username": "admin"}),
            _json_response(200, {"id": 1, "name": "Warren"}),
        ]
        fake_http = _FakeHttpxClient(responses)
        client = BackendClient(client=fake_http)

        await client.initialize_agent("Warren", initial_balance=10000.0)

        state_call = fake_http.calls[1]
        assert state_call["headers"].get("Authorization") == "Bearer jwt-xyz"

    @pytest.mark.asyncio
    async def test_401_triggers_relogin_once_then_retries(self):
        """A 401 from the backend should invalidate the cached token, re-login, and retry once."""
        responses = [
            _json_response(200, {"token": "jwt-old", "username": "admin"}),
            _json_response(401),
            _json_response(200, {"token": "jwt-new", "username": "admin"}),
            _json_response(200, {"id": 99, "name": "Warren"}),
        ]
        fake_http = _FakeHttpxClient(responses)
        client = BackendClient(client=fake_http)

        agent_id = await client.initialize_agent("Warren", initial_balance=10000.0)

        assert agent_id == 99
        assert len(fake_http.calls) == 4
        # Calls: login -> first state call (401) -> re-login -> retry state call
        assert fake_http.calls[0]["url"].endswith("/api/auth/login")
        assert fake_http.calls[1]["headers"].get("Authorization") == "Bearer jwt-old"
        assert fake_http.calls[2]["url"].endswith("/api/auth/login")
        assert fake_http.calls[3]["headers"].get("Authorization") == "Bearer jwt-new"

    @pytest.mark.asyncio
    async def test_second_401_fails_loudly(self):
        """If the retried call also returns 401, the client must surface an error."""
        responses = [
            _json_response(200, {"token": "jwt-1", "username": "admin"}),
            _json_response(401),
            _json_response(200, {"token": "jwt-2", "username": "admin"}),
            _json_response(401),
        ]
        fake_http = _FakeHttpxClient(responses)
        client = BackendClient(client=fake_http)

        with pytest.raises(BackendAPIError) as exc_info:
            await client.initialize_agent("Warren", initial_balance=10000.0)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_token_cached_across_calls(self):
        """A single login is reused across multiple state-changing calls."""
        responses = [
            _json_response(200, {"token": "jwt-cache", "username": "admin"}),
            _json_response(200, {"id": 1, "name": "Warren"}),
            _json_response(
                200,
                {
                    "agentName": "Warren",
                    "balance": 10000.0,
                    "holdings": [],
                    "holdingsValue": 0.0,
                    "totalPortfolioValue": 10000.0,
                    "initialBalance": 10000.0,
                    "totalProfitLoss": 0.0,
                    "profitLossPercent": 0.0,
                    "holdingsCount": 0,
                    "transactionCount": 0,
                },
            ),
        ]
        fake_http = _FakeHttpxClient(responses)
        client = BackendClient(client=fake_http)

        await client.initialize_agent("Warren", initial_balance=10000.0)
        await client.get_account_report(agent_id=1)

        # Exactly one login was performed (first call), the rest reused the cached token.
        login_count = sum(
            1 for c in fake_http.calls if c["url"].endswith("/api/auth/login")
        )
        assert login_count == 1
        # The account-report call must also carry the bearer header.
        assert fake_http.calls[2]["headers"].get("Authorization") == "Bearer jwt-cache"
