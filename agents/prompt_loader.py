"""Prompt Template Loader

Loads prompt templates from the prompts/ directory for Market Analyst and Decision Maker agents.

Uses composed mode: base template + personality file (base.txt + {agent_name}.personality.txt).
Shared content lives in base.txt with placeholders; per-agent personality in small personality files.

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


class _PartialFormatDict(dict):
    """Dict subclass that preserves unresolved placeholders during format_map.

    Returns '{key}' for missing keys instead of raising KeyError,
    enabling multi-stage template composition (personality -> runtime).
    """

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def _parse_personality_file(content: str) -> dict[str, str]:
    """Parse a personality file into a dict of key-value pairs.

    Format:
        key: single-line value
        key:
        multi-line value
        continues here

    A new key starts when a line matches the pattern: word_chars + colon + space/newline.
    Everything until the next key is the value for the current key.

    Args:
        content: Raw text content of personality file

    Returns:
        Dict mapping field names to their string values (stripped)
    """
    result: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    def _save_current():
        """Save current key with value, stripping only leading/trailing blank lines."""
        if current_key is None:
            return
        # Strip leading/trailing blank lines but preserve internal indentation
        lines = current_lines
        while lines and not lines[0].strip():
            lines = lines[1:]
        while lines and not lines[-1].strip():
            lines = lines[:-1]
        result[current_key] = "\n".join(lines)

    for line in content.split("\n"):
        # Check if this line starts a new key
        # Pattern: identifier (letters, digits, underscore) followed by colon
        colon_pos = line.find(":")
        if colon_pos > 0 and line[:colon_pos].replace("_", "").isalnum():
            # Save previous key if any
            _save_current()

            current_key = line[:colon_pos].strip()
            # Value starts after the colon (may be on same line or next lines)
            value_start = line[colon_pos + 1:]
            if value_start.strip():
                # Single-line value: strip leading space after colon
                current_lines = [value_start.lstrip(" ")]
            else:
                current_lines = []
        else:
            # Continuation of current key's value
            if current_key is not None:
                current_lines.append(line)

    # Save last key
    _save_current()

    return result


def load_personality(agent_type: AgentType, agent_name: str) -> dict[str, str]:
    """Load personality fields for an agent.

    Args:
        agent_type: Either "market_analyst" or "decision_maker"
        agent_name: Agent name (e.g., "Warren")

    Returns:
        Dict of personality field name -> value

    Raises:
        FileNotFoundError: If personality file doesn't exist
        ValueError: If agent_name is not valid
    """
    agent_name_lower = agent_name.lower()

    if agent_name_lower not in VALID_AGENT_NAMES:
        raise ValueError(
            f"Invalid agent name: {agent_name}. "
            f"Valid names: {', '.join(VALID_AGENT_NAMES)}"
        )

    personality_path = PROMPTS_DIR / agent_type / f"{agent_name_lower}.personality.txt"

    if not personality_path.exists():
        raise FileNotFoundError(
            f"Personality file not found: {personality_path}. "
            f"Expected at: prompts/{agent_type}/{agent_name_lower}.personality.txt"
        )

    content = personality_path.read_text(encoding="utf-8")
    fields = _parse_personality_file(content)
    logger.debug(
        f"Loaded personality for {agent_type}/{agent_name_lower} "
        f"({len(fields)} fields: {', '.join(fields.keys())})"
    )

    return fields


def load_base_template(agent_type: AgentType) -> str:
    """Load the base template for an agent type.

    Args:
        agent_type: Either "market_analyst" or "decision_maker"

    Returns:
        Base template string with placeholders

    Raises:
        FileNotFoundError: If base.txt doesn't exist
    """
    base_path = PROMPTS_DIR / agent_type / "base.txt"

    if not base_path.exists():
        raise FileNotFoundError(
            f"Base template not found: {base_path}. "
            f"Expected at: prompts/{agent_type}/base.txt"
        )

    template = base_path.read_text(encoding="utf-8")
    logger.debug(f"Loaded base template for {agent_type} ({len(template)} chars)")

    return template


def load_composed_prompt(agent_type: AgentType, agent_name: str) -> str:
    """Load base template and compose with agent personality.

    Reads the shared base template and the agent-specific personality file,
    then substitutes personality fields into the base template placeholders.

    Personality substitution is STRICT: any placeholder in the base template
    that is not present in the personality file will raise KeyError.

    Runtime placeholders (e.g., {datetime}) must be escaped as {{datetime}}
    in the base template so str.format() preserves them for later substitution.

    Args:
        agent_type: Either "market_analyst" or "decision_maker"
        agent_name: Agent name (e.g., "Warren")

    Returns:
        Composed template string (still has {datetime} placeholder for runtime)

    Raises:
        FileNotFoundError: If base template or personality file not found
        ValueError: If agent_name is not valid
        KeyError: If base template has a personality placeholder not in personality file
    """
    base = load_base_template(agent_type)
    personality = load_personality(agent_type, agent_name)

    # Strict substitution: crashes on missing personality keys.
    # Runtime placeholders like {datetime} are escaped as {{datetime}} in base
    # templates, so str.format() preserves them as {datetime} in the output.
    composed = base.format(**personality)
    logger.debug(
        f"Composed prompt for {agent_type}/{agent_name.lower()} ({len(composed)} chars)"
    )

    return composed


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
        Dict mapping agent_type to list of agent names with personality files
    """
    result = {}

    for agent_type in ["market_analyst", "decision_maker"]:
        type_dir = PROMPTS_DIR / agent_type
        if type_dir.exists():
            agents = [
                f.stem.replace(".personality", "")
                for f in type_dir.glob("*.personality.txt")
                if f.stem.replace(".personality", "") in VALID_AGENT_NAMES
            ]
            result[agent_type] = sorted(agents)
        else:
            result[agent_type] = []

    return result
