"""Agent roster — single source of truth."""

from typing import Final

AGENT_NAMES: Final[tuple[str, ...]] = ("Warren", "George", "Ray", "Cathie")

VALID_AGENT_NAMES: Final[frozenset[str]] = frozenset(n.lower() for n in AGENT_NAMES)
