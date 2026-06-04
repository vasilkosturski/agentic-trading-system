"""Tests for I9: single source of truth for the agent roster.

The four canonical agent names (Warren, George, Ray, Cathie) must be defined
in exactly one place. ``prompt_loader.VALID_AGENT_NAMES`` and
``trading_system.AGENT_CONFIGS`` must both derive from that canonical source
without re-listing the names as string literals.
"""

import re
from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parent.parent
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


def test_prompt_loader_does_not_re_list_agent_names_as_literals():
    """The four canonical name string literals appear ONLY in agent_registry.py.

    prompt_loader.py must not contain its own ``{"warren", "george", ...}``
    literal (only the import from agent_registry). We look for the
    *quoted* form so docstring prose mentioning a name (e.g. as an example
    arg value) does not trip the check — only code-level string literals
    in a set/list do.
    """
    text = (AGENTS_DIR / "infra" / "prompt_loader.py").read_text()
    text_no_imports = re.sub(r"^(from|import)\s+.*$", "", text, flags=re.MULTILINE)
    # Detect the original duplicated roster shape: a set/list literal that
    # contains all four lowercase names as quoted strings.
    roster_re = re.compile(
        r"[\{\[][^\}\]]*"
        r"(?=.*[\"']warren[\"'])"
        r"(?=.*[\"']george[\"'])"
        r"(?=.*[\"']ray[\"'])"
        r"(?=.*[\"']cathie[\"'])"
        r"[^\}\]]*[\}\]]",
        re.IGNORECASE | re.DOTALL,
    )
    assert roster_re.search(text_no_imports) is None, (
        "infra/prompt_loader.py still contains a literal set/list of the four "
        "canonical agent names — it should import VALID_AGENT_NAMES from "
        "agent_registry instead."
    )


def test_trading_system_does_not_re_list_agent_names_as_literals():
    """The agent-name string literals only live in agent_registry.py — the
    AGENT_CONFIGS table in trading_system.py must reference them, not repeat
    them."""
    text = (AGENTS_DIR / "trading_system.py").read_text()
    text_no_imports = re.sub(r"^(from|import)\s+.*$", "", text, flags=re.MULTILINE)
    # Be tolerant of any unrelated word collisions: only flag exact quoted
    # occurrences like '"Warren"' or "'Warren'".
    for name in {"Warren", "George", "Ray", "Cathie"}:
        for quoted in (f'"{name}"', f"'{name}'"):
            assert quoted not in text_no_imports, (
                f"trading_system.py still contains the canonical agent name "
                f"literal {quoted} outside of import statements."
            )
