"""Async-fetch composed prompts from Java backend, in-process cache."""

import asyncio
import logging
import os
from datetime import datetime
from typing import Literal

from agent_registry import VALID_AGENT_NAMES
from backend.client import BackendClient, get_backend_client

logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")

AgentType = Literal["market_analyst", "decision_maker"]


_PROMPT_CACHE: dict[tuple[str, str], str] = {}

# Lazily created because asyncio.Lock binds to the running event loop (which
# doesn't exist at module import time).
_cache_lock: asyncio.Lock | None = None


def clear_prompt_cache() -> None:
    _PROMPT_CACHE.clear()


def _get_cache_lock() -> asyncio.Lock:
    global _cache_lock
    if _cache_lock is None:
        _cache_lock = asyncio.Lock()
    return _cache_lock


def _get_backend_client() -> BackendClient:
    return get_backend_client()


class _PartialFormatDict(dict):
    """Dict subclass that preserves unresolved placeholders during format_map.

    Returns '{key}' for missing keys instead of raising KeyError, enabling
    runtime placeholder composition.
    """

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


async def load_composed_prompt(agent_type: AgentType, agent_name: str) -> str:
    agent_name_lower = agent_name.lower()

    if agent_name_lower not in VALID_AGENT_NAMES:
        raise ValueError(
            f"Invalid agent name: {agent_name}. Valid names: {', '.join(VALID_AGENT_NAMES)}"
        )

    cache_key = (agent_type, agent_name_lower)

    # Fast path: cached value, no lock needed (dict reads are atomic in CPython
    # and entries are never mutated or deleted in production).
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
            response = await client.request("GET", url)
            prompt = response.text
        except Exception as e:
            # Surface 404 as FileNotFoundError to preserve the previous
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
    agent_name_lower = agent_name.lower()

    if agent_name_lower not in VALID_AGENT_NAMES:
        raise ValueError(
            f"Invalid agent name: {agent_name}. Valid names: {', '.join(VALID_AGENT_NAMES)}"
        )

    return await load_composed_prompt(agent_type, agent_name)


def format_prompt(
    template: str,
    **kwargs,
) -> str:
    # Missing placeholders are left as-is (no error).
    if "datetime" not in kwargs:
        kwargs["datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return template.format_map(_PartialFormatDict(**kwargs))


async def load_and_format_prompt(
    agent_type: AgentType,
    agent_name: str,
    **kwargs,
) -> str:
    template = await load_prompt_template(agent_type, agent_name)
    return format_prompt(template, **kwargs)


def get_available_templates() -> dict[str, list[str]]:
    return {
        "market_analyst": list(VALID_AGENT_NAMES),
        "decision_maker": list(VALID_AGENT_NAMES),
    }
