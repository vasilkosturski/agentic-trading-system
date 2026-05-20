"""Telemetry helpers — SDK RunResult/Usage → backend DTO translators.

Two pure functions that translate openai-agents SDK telemetry objects into
the typed DTOs the backend consumes:

* ``extract_usage_metrics`` reads a ``Usage`` object (token counts +
  optional model-name override from request entries) and produces a
  ``UsageMetrics`` DTO with an attached ``costUsd`` computed via the
  ``MODEL_PRICING`` table. Unknown models log a warning once via the
  shared ``_UNKNOWN_MODELS_WARNED`` set and serialize ``costUsd`` as
  ``None`` so analytics don't silently aggregate wrong values.

* ``extract_run_telemetry`` is the DRY helper both phase runners
  (``_run_market_analyst`` and ``_run_decision_maker`` in
  ``agent_executor.py``) call to extract the tool-calls list + usage
  metrics from a ``RunResult``. It also emits the two observable INFO
  log lines so refactors don't silently regress observability.

Extracted from ``agent_executor.py`` (Task 2 of the decomposition plan at
``docs/superpowers/plans/2026-05-13-aegr-decomposition.md``). Zero
coupling to ``AgentExecutor`` — ``extract_run_telemetry`` was a method
that never used ``self``, so the lift to a module function is mechanical.
"""

import logging

from agents import Usage, RunResult

from infra.pricing import MODEL_PRICING, _UNKNOWN_MODELS_WARNED
from models.usage_metrics import UsageMetrics
from models.run_tracking import ToolCallDto
from utils.sdk_parser import extract_tool_calls

logger = logging.getLogger(__name__)


def extract_usage_metrics(usage: Usage, model_name: str) -> UsageMetrics:
    """Extract token usage metrics from SDK RunResultBase.context_wrapper.usage.

    Args:
        usage: Usage object from result.context_wrapper.usage
        model_name: Model name passed to Agent() constructor (fallback if
            SDK doesn't provide it).

    Returns:
        UsageMetrics with token metric fields matching backend DTOs.
    """
    cached = 0
    if usage.input_tokens_details:
        cached = getattr(usage.input_tokens_details, 'cached_tokens', 0) or 0

    reasoning = 0
    if usage.output_tokens_details:
        reasoning = getattr(usage.output_tokens_details, 'reasoning_tokens', 0) or 0

    # Try SDK first, fall back to the model name we passed to Agent()
    sdk_model = None
    if usage.request_usage_entries:
        sdk_model = getattr(usage.request_usage_entries[0], 'model_name', None)

    resolved_name: str = sdk_model if sdk_model is not None else model_name

    input_tokens = usage.input_tokens or 0
    output_tokens = usage.output_tokens or 0

    pricing = MODEL_PRICING.get(resolved_name)
    cost_usd: float | None
    if pricing is None:
        if resolved_name not in _UNKNOWN_MODELS_WARNED:
            logger.warning(
                f"No pricing entry for model {resolved_name!r}; costUsd will be None. "
                f"Refresh agents/model_prices.json (see MODEL_PRICES_README.md)."
            )
            _UNKNOWN_MODELS_WARNED.add(resolved_name)
        cost_usd = None
    else:
        input_per_m, output_per_m = pricing
        cost_usd = round((input_tokens * input_per_m + output_tokens * output_per_m) / 1_000_000, 6)

    return UsageMetrics(
        tokensUsed=usage.total_tokens,
        inputTokens=input_tokens,
        outputTokens=output_tokens,
        numTurns=usage.requests,
        cachedTokens=cached,
        reasoningTokens=reasoning,
        modelName=resolved_name,
        costUsd=cost_usd,
    )


def extract_run_telemetry(
    result: RunResult,
    model_name: str,
    agent_label: str,
) -> tuple[list[ToolCallDto], UsageMetrics]:
    """Extract tool calls + usage metrics from an SDK RunResult and log both.

    Used by `_run_market_analyst` and `_run_decision_maker` to keep both
    agent runners structurally symmetric.
    """
    parsed_calls = extract_tool_calls(result.new_items)
    tool_calls = [
        ToolCallDto(
            tool=pc.name,
            params=pc.params,
            error=pc.is_error if pc.is_error else None,
            errorMessage=pc.error_message,
        )
        for pc in parsed_calls
    ]
    logger.info(f"🔧 {agent_label} made {len(tool_calls)} tool calls")

    usage = result.context_wrapper.usage
    usage_metrics = extract_usage_metrics(usage, model_name=model_name)
    logger.info(
        f"📊 {agent_label} usage: {usage_metrics.tokensUsed} tokens, "
        f"model={usage_metrics.modelName}"
    )
    return tool_calls, usage_metrics
