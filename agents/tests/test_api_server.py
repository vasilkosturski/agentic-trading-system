"""Tests for TradingAPIServer thread-safe asyncio bridge.

Covers E2: TradingAPIServer must accept the asyncio event loop explicitly and
use it (not the undocumented ``Event._loop`` attribute) when scheduling
``manual_cycle_event.set`` from the Flask handler thread.
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from api_server import TradingAPIServer


@pytest.fixture
def manual_cycle_event() -> asyncio.Event:
    """A real asyncio.Event used as the cross-thread signal."""
    return asyncio.Event()


@pytest.fixture
def cycle_running_flag() -> dict:
    """Mutable dict tracking whether a cycle is currently running."""
    return {"running": False}


@pytest.fixture
def mock_loop() -> MagicMock:
    """A mock standing in for the asyncio event loop running in the main thread.

    We mock it so we can assert ``call_soon_threadsafe`` is invoked with the
    bound ``manual_cycle_event.set`` callable.
    """
    return MagicMock(spec=asyncio.AbstractEventLoop)


@pytest.fixture
def api_server(mock_loop, manual_cycle_event, cycle_running_flag):
    """TradingAPIServer wired with a mock loop and real event/flag."""
    return TradingAPIServer(
        trading_system=MagicMock(),
        manual_cycle_event=manual_cycle_event,
        cycle_running_flag=cycle_running_flag,
        loop=mock_loop,
    )


def test_init_stores_loop_as_self_loop(api_server, mock_loop):
    """The constructor must store the loop on ``self._loop`` so the Flask
    handler can call ``self._loop.call_soon_threadsafe(...)``."""
    assert api_server._loop is mock_loop


def test_trigger_cycle_uses_self_loop_call_soon_threadsafe(
    api_server, mock_loop, manual_cycle_event, cycle_running_flag
):
    """The /api/trigger-cycle handler must schedule ``manual_cycle_event.set``
    via the explicitly-passed loop's ``call_soon_threadsafe``, not via the
    private ``Event._loop`` attribute."""
    cycle_running_flag["running"] = False

    client = api_server.app.test_client()
    response = client.post("/api/trigger-cycle")

    assert response.status_code == 202
    mock_loop.call_soon_threadsafe.assert_called_once_with(manual_cycle_event.set)


def test_trigger_cycle_does_not_touch_event_private_loop_attr(
    api_server, mock_loop, manual_cycle_event, cycle_running_flag
):
    """Regression guard: even if asyncio.Event happens to expose ``_loop``,
    the handler must not rely on it. We verify the call was made on the
    explicit loop reference, which is the only ``call_soon_threadsafe`` we
    expose via mocking."""
    cycle_running_flag["running"] = False

    client = api_server.app.test_client()
    client.post("/api/trigger-cycle")

    # The mock loop received exactly one call_soon_threadsafe call.
    assert mock_loop.call_soon_threadsafe.call_count == 1


def test_trigger_cycle_rejects_when_already_running(
    api_server, mock_loop, cycle_running_flag
):
    """When a cycle is in progress the handler must return 409 and must NOT
    schedule another set() on the loop."""
    cycle_running_flag["running"] = True

    client = api_server.app.test_client()
    response = client.post("/api/trigger-cycle")

    assert response.status_code == 409
    mock_loop.call_soon_threadsafe.assert_not_called()


# ============================================================================
# Additional manual_cycle / health endpoint coverage (I11)
# ============================================================================


def test_init_stores_all_dependencies(
    api_server, mock_loop, manual_cycle_event, cycle_running_flag
):
    """The constructor must store every collaborator as an attribute so the
    Flask handler thread can reach the trading system, the event, and the
    cycle-running flag without touching globals."""
    assert api_server._loop is mock_loop
    assert api_server.manual_cycle_event is manual_cycle_event
    assert api_server.cycle_running_flag is cycle_running_flag
    # ``trading_system`` is the MagicMock supplied in the fixture
    assert api_server.trading_system is not None
    # Flask app is wired up and ready
    assert api_server.app is not None


def test_health_endpoint_returns_200_with_expected_body(api_server):
    """``GET /health`` is a load-balancer probe — it must return 200 with a
    machine-readable JSON status payload identifying this service."""
    client = api_server.app.test_client()
    response = client.get("/health")

    assert response.status_code == 200
    body = response.get_json()
    assert body == {"status": "healthy", "service": "trading-agents-api"}


def test_trigger_cycle_success_body_shape(
    api_server, mock_loop, cycle_running_flag
):
    """On 202 the body must include both a human message and the
    machine-readable status flag ``TRIGGERED`` so the frontend can
    differentiate this from the 409 ALREADY_RUNNING path."""
    cycle_running_flag["running"] = False

    client = api_server.app.test_client()
    response = client.post("/api/trigger-cycle")

    assert response.status_code == 202
    body = response.get_json()
    assert body["status"] == "TRIGGERED"
    assert "message" in body
    assert isinstance(body["message"], str) and body["message"]


def test_trigger_cycle_409_body_shape(
    api_server, mock_loop, cycle_running_flag
):
    """On 409 the body must carry status ``ALREADY_RUNNING`` so callers can
    distinguish a duplicate-trigger rejection from any other failure."""
    cycle_running_flag["running"] = True

    client = api_server.app.test_client()
    response = client.post("/api/trigger-cycle")

    assert response.status_code == 409
    body = response.get_json()
    assert body["status"] == "ALREADY_RUNNING"
    assert "message" in body
    assert isinstance(body["message"], str) and body["message"]


def test_health_does_not_touch_loop_or_event(
    api_server, mock_loop, manual_cycle_event, cycle_running_flag
):
    """The health probe is a read-only check — it must NOT schedule anything
    on the loop or touch the manual-cycle event."""
    client = api_server.app.test_client()
    response = client.get("/health")

    assert response.status_code == 200
    mock_loop.call_soon_threadsafe.assert_not_called()
    assert not manual_cycle_event.is_set()
    assert cycle_running_flag == {"running": False}
