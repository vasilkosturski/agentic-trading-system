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

from backend.client import BackendClient
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


def _complete_run_data() -> CompleteRunData:
    return CompleteRunData(decision=DecisionPhaseData(decision=TradeDecision.HOLD))


class TestRetryOnTransientErrors:
    """Idempotent methods retry on httpx transient errors and succeed."""

    # The retry semantics are uniform across all five idempotent methods —
    # one transient httpx error followed by a successful response should yield
    # exactly two attempts. Each row supplies the method, its kwargs, and the
    # success payload + result-shape check (None for void returns).
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method_name, kwargs, response_payload, result_check",
        [
            (
                "get_account_report",
                {"agent_id": 1},
                _account_report_payload(),
                lambda r: isinstance(r, AccountReport),
            ),
            (
                "get_recent_activity",
                {"agent_id": 1, "days": 7},
                _recent_activity_payload(),
                lambda r: isinstance(r, RecentActivityResponse),
            ),
            (
                "create_run",
                {"agent_id": 1},
                {"runId": 42},
                lambda r: r == 42,
            ),
            (
                "update_phase",
                {"run_id": 42, "phase": "RESEARCHING"},
                {},
                lambda r: r is None,
            ),
            (
                "complete_run",
                {"run_id": 42, "data": _complete_run_data()},
                {},
                lambda r: r is None,
            ),
        ],
    )
    async def test_idempotent_methods_retry_then_succeed(
        self, method_name, kwargs, response_payload, result_check
    ):
        client = BackendClient(client=AsyncMock(spec=httpx.AsyncClient))
        _disable_waits(client)

        good_response = _make_response(response_payload)

        client._request = AsyncMock(  # type: ignore[method-assign]
            side_effect=[_make_request_error(), good_response]
        )

        result = await getattr(client, method_name)(**kwargs)

        assert result_check(result)
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
    @pytest.mark.parametrize("method_name", ["buy_shares", "sell_shares"])
    async def test_trade_method_does_not_retry(self, method_name: str):
        client = BackendClient(client=AsyncMock(spec=httpx.AsyncClient))

        client._request = AsyncMock(  # type: ignore[method-assign]
            side_effect=[_make_request_error()]
        )

        with pytest.raises(httpx.RequestError):
            await getattr(client, method_name)(agent_id=1, symbol="AAPL", quantity=10)

        assert client._request.await_count == 1
