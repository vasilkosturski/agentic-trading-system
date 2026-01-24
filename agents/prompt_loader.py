"""Prompt Template Loader

Loads prompt templates from the prompts/ directory for Market Analyst and Decision Maker agents.
Templates contain full personality and instructions with placeholders for runtime data.

Per design document: system-design/workflows/trade-execution/trade_exec_workflow_design.md
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# Base directory for prompt templates (relative to this file)
PROMPTS_DIR = Path(__file__).parent / "prompts"

# Valid agent types
AgentType = Literal["market_analyst", "decision_maker"]

# Valid agent names (lowercase for file lookup)
VALID_AGENT_NAMES = {"warren", "george", "ray", "cathie"}


def load_prompt_template(agent_type: AgentType, agent_name: str) -> str:
    """Load prompt template for an agent.

    Args:
        agent_type: Either "market_analyst" or "decision_maker"
        agent_name: Agent name (e.g., "Warren", "George", "Ray", "Cathie")

    Returns:
        Template string with placeholders (e.g., {datetime}, {balance})

    Raises:
        FileNotFoundError: If template file doesn't exist
        ValueError: If agent_name is not valid
    """
    # Normalize agent name to lowercase for file lookup
    agent_name_lower = agent_name.lower()

    if agent_name_lower not in VALID_AGENT_NAMES:
        raise ValueError(
            f"Invalid agent name: {agent_name}. "
            f"Valid names: {', '.join(VALID_AGENT_NAMES)}"
        )

    # Build template path
    template_path = PROMPTS_DIR / agent_type / f"{agent_name_lower}.txt"

    if not template_path.exists():
        raise FileNotFoundError(
            f"Template not found: {template_path}. "
            f"Expected template at: prompts/{agent_type}/{agent_name_lower}.txt"
        )

    # Read and return template
    template = template_path.read_text(encoding="utf-8")
    logger.debug(f"Loaded template for {agent_type}/{agent_name_lower} ({len(template)} chars)")

    return template


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
    class SafeDict(dict):
        def __missing__(self, key):
            return f"{{{key}}}"  # Return placeholder as-is

    return template.format_map(SafeDict(**kwargs))


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
        Dict mapping agent_type to list of agent names with templates
    """
    result = {}

    for agent_type in ["market_analyst", "decision_maker"]:
        type_dir = PROMPTS_DIR / agent_type
        if type_dir.exists():
            templates = [
                f.stem for f in type_dir.glob("*.txt")
                if f.stem in VALID_AGENT_NAMES
            ]
            result[agent_type] = sorted(templates)
        else:
            result[agent_type] = []

    return result
