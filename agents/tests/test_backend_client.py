"""Tests for backend_client.py - HTTP client error handling.

Tests focus on ensuring the HTTP client properly handles error responses
and enforces JSON content negotiation via Accept headers.
"""

import asyncio

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

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
            "instance": "/api/market/INVALID"
        }

        mock_json_response = httpx.Response(
            status_code=404,
            json=json_error_body,
            headers={"content-type": "application/json"}
        )

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.request.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=httpx.Request("GET", "http://test.com/api/market/INVALID"),
            response=mock_json_response
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
            '{"tradeId":42,"symbol":"AAPL","quantity":10,'
            '"price":150.0,"newBalance":98500.0}'
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
            '{"tradeId":43,"symbol":"AAPL","quantity":5,'
            '"price":151.0,"newBalance":99255.0}'
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
