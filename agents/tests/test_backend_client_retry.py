"""Tests for backend_client retry/backoff behavior (W3 - tenacity).

Covers:
- Idempotent methods retry on transient httpx errors and eventually succeed.
- Trade methods (buy/sell) do NOT retry — they fail on the first transient error.
- Max-attempts (3) is honored — after 3 failed attempts, the error propagates.

The decorator wraps the public methods with tenacity's @retry using
retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)). Tests
mock the inner ``_request`` method to raise raw httpx errors so the retry
decorator on the public method observes them.

Wait time is neutralized in these tests by patching the wait strategy on
each decorated method's ``retry`` attribute (tenacity exposes this) to
``wait_none()``, which keeps tests fast and deterministic.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest
import tenacity

from backend_client import BackendClient
from models.api_responses import AccountReport, RecentActivityResponse
from models.run_tracking import (
    CompleteRunData,
    DecisionPhaseData,
    TradeDecision,
)


# ---------- helpers ----------


def _disable_waits(client: BackendClient) -> None:
    """Patch wait strategy on every retried method to wait_none() for fast tests."""
    methods = [
        client.get_account_report,
        client.get_recent_activity,
        client.create_run,
        client.update_phase,
        client.complete_run,
    ]
    for m in methods:
        retry_attr = getattr(m, "retry", None)
        if retry_attr is not None:
            retry_attr.wait = tenacity.wait_none()


def _account_report_payload() -> dict:
    """Minimal AccountReport payload that passes pydantic validation."""
    return {
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
    }


def _recent_activity_payload() -> dict:
    return {
        "agentName": "Warren",
        "days": 7,
        "runs": [],
        "totalRuns": 0,
        "totalTrades": 0,
    }


def _make_response(json_body: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=json_body,
        headers={"content-type": "application/json"},
    )


def _make_request_error() -> httpx.RequestError:
    """Create a real httpx.RequestError instance."""
    return httpx.RequestError(
        "transient network error",
        request=httpx.Request("GET", "http://test/api"),
    )


# ---------- retry-on-transient: get_account_report ----------


class TestRetryOnTransientErrors:
    """Idempotent methods retry on httpx transient errors and succeed."""

    @pytest.mark.asyncio
    async def test_get_account_report_retries_then_succeeds(self):
        client = BackendClient(client=AsyncMock(spec=httpx.AsyncClient))
        _disable_waits(client)

        good_response = _make_response(_account_report_payload())

        client._request = AsyncMock(  # type: ignore[method-assign]
            side_effect=[_make_request_error(), good_response]
        )

        report = await client.get_account_report(agent_id=1)

        assert isinstance(report, AccountReport)
        assert client._request.await_count == 2

    @pytest.mark.asyncio
    async def test_get_recent_activity_retries_then_succeeds(self):
        client = BackendClient(client=AsyncMock(spec=httpx.AsyncClient))
        _disable_waits(client)

        good_response = _make_response(_recent_activity_payload())

        client._request = AsyncMock(  # type: ignore[method-assign]
            side_effect=[_make_request_error(), good_response]
        )

        result = await client.get_recent_activity(agent_id=1, days=7)

        assert isinstance(result, RecentActivityResponse)
        assert client._request.await_count == 2

    @pytest.mark.asyncio
    async def test_create_run_retries_then_succeeds(self):
        client = BackendClient(client=AsyncMock(spec=httpx.AsyncClient))
        _disable_waits(client)

        good_response = _make_response({"runId": 42})

        client._request = AsyncMock(  # type: ignore[method-assign]
            side_effect=[_make_request_error(), good_response]
        )

        run_id = await client.create_run(agent_id=1)

        assert run_id == 42
        assert client._request.await_count == 2

    @pytest.mark.asyncio
    async def test_update_phase_retries_then_succeeds(self):
        client = BackendClient(client=AsyncMock(spec=httpx.AsyncClient))
        _disable_waits(client)

        good_response = _make_response({})

        client._request = AsyncMock(  # type: ignore[method-assign]
            side_effect=[_make_request_error(), good_response]
        )

        await client.update_phase(run_id=42, phase="RESEARCHING")

        assert client._request.await_count == 2

    @pytest.mark.asyncio
    async def test_complete_run_retries_then_succeeds(self):
        client = BackendClient(client=AsyncMock(spec=httpx.AsyncClient))
        _disable_waits(client)

        good_response = _make_response({})

        client._request = AsyncMock(  # type: ignore[method-assign]
            side_effect=[_make_request_error(), good_response]
        )

        data = CompleteRunData(
            decision=DecisionPhaseData(decision=TradeDecision.HOLD),
        )

        await client.complete_run(run_id=42, data=data)

        assert client._request.await_count == 2


# ---------- max-attempts honored ----------


class TestMaxAttemptsHonored:
    """After 3 failed attempts the underlying httpx error propagates."""

    @pytest.mark.asyncio
    async def test_get_account_report_gives_up_after_three_attempts(self):
        client = BackendClient(client=AsyncMock(spec=httpx.AsyncClient))
        _disable_waits(client)

        client._request = AsyncMock(  # type: ignore[method-assign]
            side_effect=[
                _make_request_error(),
                _make_request_error(),
                _make_request_error(),
            ]
        )

        with pytest.raises(httpx.RequestError):
            await client.get_account_report(agent_id=1)

        assert client._request.await_count == 3


# ---------- trade methods are NOT retried ----------


class TestTradeMethodsNotRetried:
    """buy_shares / sell_shares fail on the first transient error (no retry)."""

    @pytest.mark.asyncio
    async def test_buy_shares_does_not_retry(self):
        client = BackendClient(client=AsyncMock(spec=httpx.AsyncClient))

        client._request = AsyncMock(  # type: ignore[method-assign]
            side_effect=[_make_request_error()]
        )

        with pytest.raises(httpx.RequestError):
            await client.buy_shares(agent_id=1, symbol="AAPL", quantity=10)

        assert client._request.await_count == 1

    @pytest.mark.asyncio
    async def test_sell_shares_does_not_retry(self):
        client = BackendClient(client=AsyncMock(spec=httpx.AsyncClient))

        client._request = AsyncMock(  # type: ignore[method-assign]
            side_effect=[_make_request_error()]
        )

        with pytest.raises(httpx.RequestError):
            await client.sell_shares(agent_id=1, symbol="AAPL", quantity=10)

        assert client._request.await_count == 1
