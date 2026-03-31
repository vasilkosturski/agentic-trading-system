"""Prompt Template Loader

Fetches composed prompt templates from Java backend API.

The backend serves prompts from Java resources (backend/src/main/resources/prompts/)
which are composed from base template + personality files with placeholder substitution.

Python agents fetch composed prompts via HTTP from backend instead of reading local files.
This establishes Java as the single source of truth for all prompt content.
"""

import logging
import os
from datetime import datetime
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

# Backend base URL - read from environment or default to local
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")

# Valid agent types
AgentType = Literal["market_analyst", "decision_maker"]

# Valid agent names (lowercase for API calls)
VALID_AGENT_NAMES = {"warren", "george", "ray", "cathie"}


class _PartialFormatDict(dict):
    """Dict subclass that preserves unresolved placeholders during format_map.

    Returns '{key}' for missing keys instead of raising KeyError,
    enabling runtime placeholder composition.
    """

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def load_composed_prompt(agent_type: AgentType, agent_name: str) -> str:
    """Fetch composed prompt from Java backend API.

    The backend composes the prompt from base template + personality file
    with placeholder substitution already applied. Python agents receive
    the ready-to-use prompt template (still has runtime placeholders like {datetime}).

    Args:
        agent_type: Either "market_analyst" or "decision_maker"
        agent_name: Agent name (e.g., "Warren")

    Returns:
        Composed template string (still has {datetime} placeholder for runtime)

    Raises:
        httpx.HTTPStatusError: If backend returns error (404, 500, etc.)
        httpx.RequestError: If backend is unreachable
        ValueError: If agent_name is not valid
    """
    agent_name_lower = agent_name.lower()

    if agent_name_lower not in VALID_AGENT_NAMES:
        raise ValueError(
            f"Invalid agent name: {agent_name}. "
            f"Valid names: {', '.join(VALID_AGENT_NAMES)}"
        )

    url = f"{BACKEND_URL}/api/prompts/{agent_type}/{agent_name_lower}"

    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        prompt = response.text

        logger.debug(
            f"Fetched prompt for {agent_type}/{agent_name_lower} from backend ({len(prompt)} chars)"
        )

        return prompt

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise FileNotFoundError(
                f"Prompt not found: {agent_type}/{agent_name_lower}. "
                f"Backend returned 404 from {url}"
            ) from e
        raise
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch prompt from backend: {e}")
        raise RuntimeError(
            f"Cannot reach backend at {BACKEND_URL}. "
            f"Make sure backend is running and BACKEND_URL is correct."
        ) from e


def load_prompt_template(agent_type: AgentType, agent_name: str) -> str:
    """Load prompt template for an agent.

    Uses composed mode: base.txt + personality file.

    Args:
        agent_type: Either "market_analyst" or "decision_maker"
        agent_name: Agent name (e.g., "Warren", "George", "Ray", "Cathie")

    Returns:
        Template string with placeholders (e.g., {datetime})

    Raises:
        FileNotFoundError: If base template or personality file doesn't exist
        ValueError: If agent_name is not valid
    """
    agent_name_lower = agent_name.lower()

    if agent_name_lower not in VALID_AGENT_NAMES:
        raise ValueError(
            f"Invalid agent name: {agent_name}. "
            f"Valid names: {', '.join(VALID_AGENT_NAMES)}"
        )

    return load_composed_prompt(agent_type, agent_name)


def format_prompt(
    template: str,
    **kwargs,
) -> str:
    """Format a prompt template with runtime values.

    Args:
        template: Template string with placeholders
        **kwargs: Values to substitute (e.g., datetime="2025-01-23", balance=100000)

    Returns:
        Formatted prompt string

    Note:
        - Uses str.format() for substitution
        - Missing placeholders are left as-is (no error)
        - Extra kwargs are ignored
    """
    # Add datetime if not provided
    if "datetime" not in kwargs:
        kwargs["datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Use format_map to handle missing keys gracefully
    return template.format_map(_PartialFormatDict(**kwargs))


def load_and_format_prompt(
    agent_type: AgentType,
    agent_name: str,
    **kwargs,
) -> str:
    """Load and format a prompt template in one call.

    Args:
        agent_type: Either "market_analyst" or "decision_maker"
        agent_name: Agent name (e.g., "Warren")
        **kwargs: Values to substitute in template

    Returns:
        Formatted prompt string ready for use

    Example:
        prompt = load_and_format_prompt(
            "market_analyst",
            "Warren",
            datetime="2025-01-23 10:30:00"
        )
    """
    template = load_prompt_template(agent_type, agent_name)
    return format_prompt(template, **kwargs)


def get_available_templates() -> dict[str, list[str]]:
    """Get list of available templates by agent type.

    Returns:
        Dict mapping agent_type to list of agent names
    """
    # Hardcoded list since prompts are now in Java backend
    # All 4 agents have both market_analyst and decision_maker prompts
    return {
        "market_analyst": list(VALID_AGENT_NAMES),
        "decision_maker": list(VALID_AGENT_NAMES),
    }
