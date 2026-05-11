"""Prompt Template Loader

Fetches composed prompt templates from Java backend API.

The backend serves prompts from Java resources (backend/src/main/resources/prompts/)
which are composed from base template + personality files with placeholder substitution.

Python agents fetch composed prompts via HTTP from backend instead of reading local files.
This establishes Java as the single source of truth for all prompt content.

ARCHITECTURE NOTES (E1 fix):
----------------------------
Previously this module called sync ``httpx.get(url)`` from ``load_composed_prompt``.
Because the only callers (``create_market_analyst_agent`` /
``create_decision_maker_agent``) are themselves ``async def``, that sync call
blocked the asyncio event loop for the duration of every fetch — N agents x 2
prompt types = up to 8 blocking calls per trading cycle.

The module is now fully async:

* ``load_composed_prompt`` is ``async def`` and routes the fetch through the
  shared :class:`~backend_client.BackendClient` (its async ``_request`` method
  reuses a pooled ``httpx.AsyncClient``).
* Results are memoised in an in-process dict keyed by ``(agent_type,
  agent_name_lower)``.  Templates are static per deploy, so a cycle pays at
  most one HTTP fetch per template; subsequent calls are served from memory.
  Invalidation strategy: process restart (no TTL).
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Literal, Tuple

from backend_client import BackendClient, get_backend_client

logger = logging.getLogger(__name__)

# Backend base URL - read from environment or default to local
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")

# Valid agent types
AgentType = Literal["market_analyst", "decision_maker"]

# Valid agent names (lowercase for API calls)
VALID_AGENT_NAMES = {"warren", "george", "ray", "cathie"}


# ---------------------------------------------------------------------------
# In-process prompt cache
# ---------------------------------------------------------------------------

# Maps (agent_type, agent_name_lower) -> composed prompt template string.
# Bounded only by the cardinality of (agent_type x agent_name) — currently
# 2 x 4 = 8 entries — so an unbounded dict is safe and intentional.
_PROMPT_CACHE: Dict[Tuple[str, str], str] = {}

# Guards concurrent first-fetch races: two coroutines awaiting
# load_composed_prompt(...) for the same key must share a single HTTP call.
# Lazily created on first use because asyncio.Lock binds to the running event
# loop (which doesn't exist at module import time).
_cache_lock: asyncio.Lock | None = None


def clear_prompt_cache() -> None:
    """Empty the in-process prompt cache.

    Test-only helper — production code never calls this because templates are
    immutable for the lifetime of the process.
    """
    _PROMPT_CACHE.clear()


def _get_cache_lock() -> asyncio.Lock:
    """Return the module-level ``asyncio.Lock``, creating it on first use."""
    global _cache_lock
    if _cache_lock is None:
        _cache_lock = asyncio.Lock()
    return _cache_lock


def _get_backend_client() -> BackendClient:
    """Indirection so tests can patch the client lookup at this module's namespace."""
    return get_backend_client()


class _PartialFormatDict(dict):
    """Dict subclass that preserves unresolved placeholders during format_map.

    Returns '{key}' for missing keys instead of raising KeyError,
    enabling runtime placeholder composition.
    """

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


async def load_composed_prompt(agent_type: AgentType, agent_name: str) -> str:
    """Fetch composed prompt from Java backend API (async, cached).

    The backend composes the prompt from base template + personality file
    with placeholder substitution already applied. Python agents receive
    the ready-to-use prompt template (still has runtime placeholders like
    ``{datetime}``).

    Args:
        agent_type: Either ``"market_analyst"`` or ``"decision_maker"``.
        agent_name: Agent name (e.g., ``"Warren"`` — case-insensitive).

    Returns:
        Composed template string (still has ``{datetime}`` placeholder for
        runtime).

    Raises:
        ValueError: If ``agent_name`` is not in :data:`VALID_AGENT_NAMES`.
        FileNotFoundError: If backend returns 404 for this agent.
        BackendAPIError: For any other backend / network failure (propagated
            from :meth:`BackendClient._request`).
    """
    agent_name_lower = agent_name.lower()

    if agent_name_lower not in VALID_AGENT_NAMES:
        raise ValueError(
            f"Invalid agent name: {agent_name}. "
            f"Valid names: {', '.join(VALID_AGENT_NAMES)}"
        )

    cache_key = (agent_type, agent_name_lower)

    # Fast path: cached value, no lock needed (dict reads are atomic in CPython
    # and we never delete or mutate entries in production).
    cached = _PROMPT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    # Slow path: serialise concurrent first-fetches for the same key behind a
    # lock so two coroutines don't both hit the backend.
    async with _get_cache_lock():
        cached = _PROMPT_CACHE.get(cache_key)
        if cached is not None:
            return cached

        url = f"{BACKEND_URL}/api/prompts/{agent_type}/{agent_name_lower}"
        try:
            client = _get_backend_client()
            response = await client._request("GET", url)
            prompt = response.text
        except Exception as e:
            # The backend client wraps HTTPStatusError as BackendAPIError; we
            # surface 404 as FileNotFoundError to preserve the previous
            # contract that callers can rely on.
            status = getattr(e, "status_code", None)
            if status == 404:
                raise FileNotFoundError(
                    f"Prompt not found: {agent_type}/{agent_name_lower}. "
                    f"Backend returned 404 from {url}"
                ) from e
            raise

        logger.debug(
            "Fetched prompt for %s/%s from backend (%d chars)",
            agent_type,
            agent_name_lower,
            len(prompt),
        )

        _PROMPT_CACHE[cache_key] = prompt
        return prompt


async def load_prompt_template(agent_type: AgentType, agent_name: str) -> str:
    """Load prompt template for an agent.

    Uses composed mode: base.txt + personality file.

    Args:
        agent_type: Either ``"market_analyst"`` or ``"decision_maker"``.
        agent_name: Agent name (e.g., ``"Warren"``).

    Returns:
        Template string with placeholders (e.g., ``{datetime}``).

    Raises:
        FileNotFoundError: If backend returns 404 for this agent.
        ValueError: If ``agent_name`` is not valid.
    """
    agent_name_lower = agent_name.lower()

    if agent_name_lower not in VALID_AGENT_NAMES:
        raise ValueError(
            f"Invalid agent name: {agent_name}. "
            f"Valid names: {', '.join(VALID_AGENT_NAMES)}"
        )

    return await load_composed_prompt(agent_type, agent_name)


def format_prompt(
    template: str,
    **kwargs,
) -> str:
    """Format a prompt template with runtime values.

    Args:
        template: Template string with placeholders.
        **kwargs: Values to substitute (e.g. ``datetime="2025-01-23"``,
            ``balance=100000``).

    Returns:
        Formatted prompt string.

    Note:
        - Uses ``str.format_map`` for substitution.
        - Missing placeholders are left as-is (no error).
        - Extra kwargs are ignored.
    """
    if "datetime" not in kwargs:
        kwargs["datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return template.format_map(_PartialFormatDict(**kwargs))


async def load_and_format_prompt(
    agent_type: AgentType,
    agent_name: str,
    **kwargs,
) -> str:
    """Load and format a prompt template in one async call.

    Args:
        agent_type: Either ``"market_analyst"`` or ``"decision_maker"``.
        agent_name: Agent name (e.g., ``"Warren"``).
        **kwargs: Values to substitute in template.

    Returns:
        Formatted prompt string ready for use.
    """
    template = await load_prompt_template(agent_type, agent_name)
    return format_prompt(template, **kwargs)


def get_available_templates() -> dict[str, list[str]]:
    """Get list of available templates by agent type.

    Returns:
        Dict mapping agent_type to list of agent names.
    """
    # Hardcoded list since prompts live in the Java backend; all 4 agents have
    # both market_analyst and decision_maker prompts.
    return {
        "market_analyst": list(VALID_AGENT_NAMES),
        "decision_maker": list(VALID_AGENT_NAMES),
    }
