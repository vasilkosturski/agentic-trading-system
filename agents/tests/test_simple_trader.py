"""Tests for SimpleTrader dataclass defaults.

``model_name`` is an *override*, not a default binding: left unset each phase
declares its own intent and the gateway resolves it. A default that eagerly read
``config.OPENAI_MODEL`` would pin both phases to one model on every cycle and
silently defeat gateway-side binding.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_agents.simple_trader import SimpleTrader, run_trader_cycle
from models.investment_style import InvestmentStyle


@pytest.fixture(autouse=True)
def no_trace_export(monkeypatch):
    """``run_trader_cycle`` opens a real SDK trace, which the backend exporter
    ships to api.openai.com. Unit tests must not make that call."""
    monkeypatch.setattr("ai_agents.simple_trader.trace", MagicMock())


def _make_trader(**overrides: Any) -> SimpleTrader:
    # Annotated: a bare heterogeneous literal infers dict[str, object], which
    # cannot be unpacked into SimpleTrader's typed fields.
    kwargs: dict[str, Any] = {
        "name": "TestTrader",
        "agent_style": InvestmentStyle.VALUE,
        "strategy": "test strategy",
        "agent_id": 999,
    }
    kwargs.update(overrides)
    return SimpleTrader(**kwargs)


def test_model_name_defaults_to_no_override():
    """No pinned model by default, so per-phase intents survive to the gateway."""
    trader = _make_trader()

    assert trader.model_name is None, (
        "a concrete default here would override every phase's intent; the gateway "
        "resolves intent → model, and the app should not pre-empt that"
    )


def test_explicit_model_name_is_preserved():
    trader = _make_trader(model_name="gpt-4o")

    assert trader.model_name == "gpt-4o"


@pytest.mark.asyncio
async def test_cycle_receives_the_traders_model_override():
    trader = _make_trader(model_name="gpt-4o")

    with patch("ai_agents.simple_trader.run_cycle", new=AsyncMock()) as p_cycle:
        await run_trader_cycle(trader, MagicMock(), force_trade=False)

    assert p_cycle.await_args.kwargs["model_name"] == "gpt-4o"


@pytest.mark.asyncio
async def test_cycle_receives_none_when_unpinned():
    trader = _make_trader()

    with patch("ai_agents.simple_trader.run_cycle", new=AsyncMock()) as p_cycle:
        await run_trader_cycle(trader, MagicMock(), force_trade=False)

    assert p_cycle.await_args.kwargs["model_name"] is None
