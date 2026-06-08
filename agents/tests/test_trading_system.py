"""Tests for TradingSystem.run_all_agents error handling and metrics.

Covers E3: asyncio.gather(return_exceptions=True) result must not be discarded.
The function must:
1. Bind the gather result to a variable.
2. zip(self.agents, results) and log per-agent Exception results at ERROR
   with agent_name in structured extras.
3. Return success/failure counts so cycle-level metrics can use them.
4. Tolerate per-agent crashes (no exception raised by run_all_agents).
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from trading_system import TradingSystem


def _make_agent(name: str) -> MagicMock:
    """Build a minimal SimpleTrader-shaped mock with a name attribute."""
    agent = MagicMock()
    agent.name = name
    agent.agent_style = "VALUE"
    return agent


@pytest.fixture
def four_agents():
    return [
        _make_agent("Warren"),
        _make_agent("George"),
        _make_agent("Ray"),
        _make_agent("Cathie"),
    ]


@pytest.fixture
def system(four_agents):
    return TradingSystem(four_agents)


async def _patch_per_agent_runner(side_effects):
    """Return a coroutine factory that, given (agent, force_trade), yields the
    next side effect — either returns None on success or raises the supplied
    exception. side_effects is a dict keyed by agent name."""

    async def fake_run_agent_with_own_mcp(agent, force_trade):
        effect = side_effects[agent.name]
        if isinstance(effect, BaseException):
            raise effect
        return effect

    return fake_run_agent_with_own_mcp


# ---------------------------------------------------------------------------
# Path 1: all-success
# ---------------------------------------------------------------------------


async def test_run_all_agents_all_success_returns_counts(system, four_agents, caplog):
    """All four agents succeed: success=4, failure=0, no ERROR logs from gather."""
    side_effects = {a.name: None for a in four_agents}
    fake_runner = await _patch_per_agent_runner(side_effects)

    with patch.object(TradingSystem, "_run_agent_with_own_mcp", side_effect=fake_runner):
        with caplog.at_level(logging.ERROR, logger="trading_system"):
            result = await system.run_all_agents()

    assert result == {"success": 4, "failure": 0}
    # No ERROR records emitted with agent_name extra (no failures)
    failure_records = [r for r in caplog.records if getattr(r, "agent_name", None) is not None]
    assert failure_records == []


# ---------------------------------------------------------------------------
# Path 2: one-failure
# ---------------------------------------------------------------------------


async def test_run_all_agents_one_failure_logs_with_agent_name(system, four_agents, caplog):
    """One agent crashes: returned counts = success=3, failure=1, and the
    failing agent's name is present in the ERROR record's structured extras."""
    boom = RuntimeError("agent boom")
    side_effects = {
        "Warren": None,
        "George": boom,
        "Ray": None,
        "Cathie": None,
    }
    fake_runner = await _patch_per_agent_runner(side_effects)

    with patch.object(TradingSystem, "_run_agent_with_own_mcp", side_effect=fake_runner):
        with caplog.at_level(logging.ERROR, logger="trading_system"):
            result = await system.run_all_agents()

    assert result == {"success": 3, "failure": 1}

    failure_records = [
        r
        for r in caplog.records
        if r.levelno == logging.ERROR and getattr(r, "agent_name", None) == "George"
    ]
    assert len(failure_records) == 1, (
        f"Expected exactly one ERROR record with agent_name='George'; "
        f"got: {[(r.levelname, getattr(r, 'agent_name', None), r.getMessage()) for r in caplog.records]}"
    )


# ---------------------------------------------------------------------------
# Path 3: all-failure
# ---------------------------------------------------------------------------


async def test_run_all_agents_all_failure_logs_each_and_no_raise(system, four_agents, caplog):
    """All agents crash: counts = success=0, failure=4. ERROR record per
    agent with the agent_name extra set. run_all_agents itself does not raise.
    """
    side_effects = {
        "Warren": RuntimeError("w"),
        "George": ValueError("g"),
        "Ray": KeyError("r"),
        "Cathie": RuntimeError("c"),
    }
    fake_runner = await _patch_per_agent_runner(side_effects)

    with patch.object(TradingSystem, "_run_agent_with_own_mcp", side_effect=fake_runner):
        with caplog.at_level(logging.ERROR, logger="trading_system"):
            result = await system.run_all_agents()

    assert result == {"success": 0, "failure": 4}

    error_agent_names = sorted(
        getattr(r, "agent_name", None)
        for r in caplog.records
        if r.levelno == logging.ERROR and getattr(r, "agent_name", None) is not None
    )
    assert error_agent_names == ["Cathie", "George", "Ray", "Warren"]


# ============================================================================
# Additional scheduler / orchestration coverage (I11)
# ============================================================================


def test_agent_configs_zips_names_with_styles_in_registry_order():
    """``AGENT_CONFIGS`` must align with ``AGENT_NAMES`` 1:1 — drift between
    the name registry and per-persona style/balance config would silently
    mis-assign personas at startup, so this test guards against re-ordering.
    """
    from agent_registry import AGENT_NAMES

    configs = TradingSystem.AGENT_CONFIGS

    assert len(configs) == len(AGENT_NAMES)
    for cfg, expected_name in zip(configs, AGENT_NAMES, strict=True):
        assert cfg["name"] == expected_name
        assert "style" in cfg
        assert "balance" in cfg
        assert isinstance(cfg["balance"], int | float)
        assert cfg["balance"] > 0


def test_print_agent_summary_runs_without_error(system, four_agents, capsys):
    """The roster banner is logged on every cycle — it must never crash, and
    each agent's name must appear in stdout so operators can see who's loaded.
    """
    # Must not raise
    system.print_agent_summary()

    out = capsys.readouterr().out
    for agent in four_agents:
        assert agent.name in out


async def test_run_all_agents_force_one_trade_forces_exactly_one_agent(system, four_agents):
    """When ``force_one_trade=True``, exactly one of the four agents must be
    invoked with ``force_trade=True`` and the other three with
    ``force_trade=False`` — never zero, never two.
    """
    captured_calls: list[tuple[str, bool]] = []

    async def capturing_runner(agent, force_trade):
        captured_calls.append((agent.name, force_trade))

    with patch.object(TradingSystem, "_run_agent_with_own_mcp", side_effect=capturing_runner):
        result = await system.run_all_agents(force_one_trade=True)

    # All four agents were invoked
    assert len(captured_calls) == 4
    assert sorted(name for name, _ in captured_calls) == ["Cathie", "George", "Ray", "Warren"]

    forced_count = sum(1 for _, forced in captured_calls if forced)
    assert forced_count == 1, (
        f"force_one_trade=True must force exactly one agent; got {forced_count} "
        f"(calls={captured_calls})"
    )
    # And the cycle still reports success counts for the run
    assert result == {"success": 4, "failure": 0}


async def test_run_all_agents_no_force_passes_force_trade_false_to_every_agent(system, four_agents):
    """The default path (``force_one_trade=False``) must NEVER force any agent
    — every agent is called with ``force_trade=False``."""
    captured_calls: list[tuple[str, bool]] = []

    async def capturing_runner(agent, force_trade):
        captured_calls.append((agent.name, force_trade))

    with patch.object(TradingSystem, "_run_agent_with_own_mcp", side_effect=capturing_runner):
        await system.run_all_agents(force_one_trade=False)

    assert len(captured_calls) == 4
    assert all(forced is False for _, forced in captured_calls), captured_calls
