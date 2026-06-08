"""Tests for I9: single source of truth for the agent roster.

The four canonical agent names (Warren, George, Ray, Cathie) must be defined
in exactly one place. ``prompt_loader.VALID_AGENT_NAMES`` and
``trading_system.AGENT_CONFIGS`` must both derive from that canonical source
without re-listing the names as string literals.
"""

CANONICAL_NAMES = {"warren", "george", "ray", "cathie"}


def test_agent_registry_exposes_canonical_names():
    """agent_registry exports VALID_AGENT_NAMES with the four canonical names."""
    from agent_registry import VALID_AGENT_NAMES

    assert VALID_AGENT_NAMES == CANONICAL_NAMES


def test_prompt_loader_reuses_registry_set():
    """infra.prompt_loader.VALID_AGENT_NAMES is the same object as the registry set
    (i.e. imported, not re-listed)."""
    from agent_registry import VALID_AGENT_NAMES as registry_set
    from infra.prompt_loader import VALID_AGENT_NAMES as loader_set

    assert loader_set is registry_set


def test_trading_system_agent_configs_use_registry_names():
    """AGENT_CONFIGS entries derive their names from the registry."""
    from agent_registry import AGENT_NAMES
    from trading_system import TradingSystem

    config_names = [cfg["name"] for cfg in TradingSystem.AGENT_CONFIGS]
    # Same names, same order, same casing as the registry's canonical list.
    assert config_names == list(AGENT_NAMES)
