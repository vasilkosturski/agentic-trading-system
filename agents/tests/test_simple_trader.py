"""Tests for SimpleTrader dataclass defaults.

Covers I5: the model_name default must be re-evaluated per-instantiation
via field(default_factory=lambda: config.OPENAI_MODEL) so runtime config
changes (e.g., tests monkeypatching config.OPENAI_MODEL) are reflected
in new SimpleTrader instances.
"""

import pytest

from config import config
from models.investment_style import InvestmentStyle
from simple_trader import SimpleTrader


def test_model_name_default_reads_current_config_value(monkeypatch):
    """SimpleTrader.model_name default must reflect the current config.OPENAI_MODEL
    at instantiation time, not the value captured when the class was defined.

    With a literal default (config.OPENAI_MODEL) the value is bound once at
    class-definition time. With field(default_factory=lambda: config.OPENAI_MODEL)
    it is re-read each time __init__ runs, which is what we want so tests and
    runtime overrides take effect.
    """
    sentinel_model = "gpt-test-i5-sentinel"
    monkeypatch.setattr(config, "OPENAI_MODEL", sentinel_model)

    trader = SimpleTrader(
        name="TestTrader",
        agent_style=InvestmentStyle.VALUE,
        strategy="test strategy",
        agent_id=999,
    )

    assert trader.model_name == sentinel_model, (
        f"model_name default should be re-evaluated from config.OPENAI_MODEL "
        f"at instantiation time, got {trader.model_name!r} instead of {sentinel_model!r}"
    )
