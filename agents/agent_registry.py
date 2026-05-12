"""Agent roster — single source of truth.

The four canonical trading-agent names live here so every other module
(``trading_system``, ``prompt_loader``, ...) references the same data
instead of repeating the literals.

Why this module exists (instead of just exposing the names from
``trading_system``):

* ``trading_system`` transitively imports ``prompt_loader`` via
  ``simple_trader -> agent_executor -> {market_analyst, decision_maker} ->
  prompt_loader``. If ``prompt_loader`` imported from ``trading_system`` to
  read the roster, that would close an import cycle.
* Pulling the names into a tiny dependency-free module breaks the cycle and
  keeps the registry import-cheap (no SDK, no httpx, no Flask).

If you add an agent, add a single entry to :data:`AGENT_NAMES` and the rest
of the system picks it up automatically.
"""

from typing import Final, Tuple


# Order is significant for the trading-system AGENT_CONFIGS table and the
# UI roster summary — keep new entries appended unless the order is
# intentionally being changed.
AGENT_NAMES: Final[Tuple[str, ...]] = ("Warren", "George", "Ray", "Cathie")

# Lowercased lookup set used by the prompt loader (the backend API URL
# segments are lowercase). Built from AGENT_NAMES so there is exactly one
# place to edit when the roster changes.
VALID_AGENT_NAMES: Final[frozenset[str]] = frozenset(n.lower() for n in AGENT_NAMES)
