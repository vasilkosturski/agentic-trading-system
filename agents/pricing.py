"""Model pricing — (input_per_1m_usd, output_per_1m_usd) per 1,000,000 tokens.

Loaded once at import time from a vendored LiteLLM pricing JSON
(`model_prices.json` sibling file). Unknown models log a warning once via
the `_UNKNOWN_MODELS_WARNED` set and serialize `costUsd` as null so
analytics don't silently aggregate wrong values.

Why vendored: OpenAI doesn't expose pricing via API
(openai/openai-python#2074 still open). LiteLLM's
`model_prices_and_context_window.json` is the de-facto industry source,
community-maintained, covers all major providers. Vendoring it makes
pricing refreshes a one-line curl + PR diff. See MODEL_PRICES_README.md.

Extracted from `agent_executor.py` (Task 1 of the decomposition plan at
`docs/superpowers/plans/2026-05-13-aegr-decomposition.md`). Zero coupling
to AgentExecutor — pure data + one loader function + a dedupe set.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PRICING_JSON_PATH = Path(__file__).parent / "model_prices.json"


def _load_model_pricing(path: Path = _PRICING_JSON_PATH) -> dict[str, tuple[float, float]]:
    """Load (input_per_1m_usd, output_per_1m_usd) pairs from a vendored LiteLLM
    pricing JSON. Skips entries that don't define both cost keys (e.g. the
    JSON's first "sample_spec" placeholder).

    LiteLLM stores `input_cost_per_token` / `output_cost_per_token` as USD
    per single token, so we multiply by 1_000_000 to match this module's
    per-1M-token convention. To refresh:

        curl -sL https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json \\
            -o agentic-trading-system/agents/model_prices.json
    """
    with path.open() as f:
        data: dict[str, Any] = json.load(f)
    pricing: dict[str, tuple[float, float]] = {}
    for name, entry in data.items():
        if not isinstance(entry, dict):
            continue
        in_per_token = entry.get("input_cost_per_token")
        out_per_token = entry.get("output_cost_per_token")
        if in_per_token is None or out_per_token is None:
            continue
        pricing[name] = (in_per_token * 1_000_000, out_per_token * 1_000_000)
    return pricing


MODEL_PRICING: dict[str, tuple[float, float]] = _load_model_pricing()
_UNKNOWN_MODELS_WARNED: set[str] = set()
