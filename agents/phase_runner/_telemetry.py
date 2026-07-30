"""SDK telemetry → backend DTO translation. Private to phase_runner.

Two pure functions both phase helpers call:
* ``extract_usage_metrics`` translates a ``Usage`` object into a ``UsageMetrics``
  DTO with an attached ``costUsd``. Cost has two possible sources and they do not
  mix: on the gateway path the proxy's own reported cost wins, because the phase
  named an intent alias that ``MODEL_PRICING`` cannot price and the gateway is
  the one that chose the model. Off the gateway path (local dev) the vendored
  ``MODEL_PRICING`` table applies. Either way an unpriceable call serializes
  ``costUsd=None`` so analytics never silently aggregate a guess.
* ``extract_run_telemetry`` is the DRY helper that pairs ``extract_tool_calls``
  (from ``utils.sdk_parser``) with ``extract_usage_metrics`` and emits the two
  observable INFO log lines.

``utils.sdk_parser`` is NOT absorbed — ``ai_agents.market_analyst`` and
``ai_agents.decision_maker`` import its tool-call extraction directly. It stays
a shared utility; this module just consumes it.
"""

import logging

from agents import RunResult, Usage

from infra.gateway_usage import GatewayUsage
from infra.pricing import _UNKNOWN_MODELS_WARNED, MODEL_PRICING
from models.run_tracking import ToolCallDto
from models.usage_metrics import UsageMetrics
from utils.sdk_parser import extract_tool_calls

logger = logging.getLogger(__name__)


def _price_locally(model_name: str, input_tokens: int, output_tokens: int) -> float | None:
    """Price a call from the vendored table. Used off the gateway path (local dev).

    Unknown models warn once via the shared ``_UNKNOWN_MODELS_WARNED`` set and
    yield ``None`` rather than a zero, so analytics never aggregate a guess.
    """
    pricing = MODEL_PRICING.get(model_name)
    if pricing is None:
        if model_name not in _UNKNOWN_MODELS_WARNED:
            logger.warning(
                f"No pricing entry for model {model_name!r}; costUsd will be None. "
                f"Refresh agents/infra/model_prices.json (see MODEL_PRICES_README.md)."
            )
            _UNKNOWN_MODELS_WARNED.add(model_name)
        return None
    input_per_m, output_per_m = pricing
    return round((input_tokens * input_per_m + output_tokens * output_per_m) / 1_000_000, 6)


def extract_usage_metrics(
    usage: Usage,
    model_name: str,
    gateway_usage: GatewayUsage | None = None,
) -> UsageMetrics:
    """Translate SDK ``Usage`` to a ``UsageMetrics`` DTO with computed cost.

    Args:
        usage: From ``result.context_wrapper.usage``.
        model_name: Model name passed to the Agent constructor (fallback when
            the SDK's ``request_usage_entries`` doesn't carry one). On the
            gateway path this is an intent alias, which ``MODEL_PRICING``
            cannot price — hence ``gateway_usage``.
        gateway_usage: What the gateway reported in its response headers, when
            the phase ran through the gateway. Authoritative for both cost and
            the concrete model: the gateway did the routing and it holds the
            current price list, so an app-side estimate would only ever be a
            stale second opinion in the same column.
    """
    cached = 0
    if usage.input_tokens_details:
        cached = getattr(usage.input_tokens_details, "cached_tokens", 0) or 0

    reasoning = 0
    if usage.output_tokens_details:
        reasoning = getattr(usage.output_tokens_details, "reasoning_tokens", 0) or 0

    sdk_model = None
    if usage.request_usage_entries:
        sdk_model = getattr(usage.request_usage_entries[0], "model_name", None)

    gateway_model = gateway_usage.model_name if gateway_usage else None
    resolved_name: str = gateway_model or sdk_model or model_name

    input_tokens = usage.input_tokens or 0
    output_tokens = usage.output_tokens or 0

    cost_usd: float | None
    if gateway_usage is not None and gateway_usage.responses:
        # The gateway priced these calls against its own model_list. Do not
        # fall back to MODEL_PRICING when it reported no cost: mixing a local
        # estimate into the same column makes the column unaggregatable.
        cost_usd = gateway_usage.cost_usd
        if cost_usd is None:
            logger.warning(
                f"Gateway reported no cost for {resolved_name!r} "
                f"({gateway_usage.responses} calls); costUsd will be None."
            )
    else:
        cost_usd = _price_locally(resolved_name, input_tokens, output_tokens)

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
    gateway_usage: GatewayUsage | None = None,
) -> tuple[list[ToolCallDto], UsageMetrics]:
    """Extract tool calls + usage metrics from a ``RunResult`` and log both."""
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
    usage_metrics = extract_usage_metrics(usage, model_name=model_name, gateway_usage=gateway_usage)
    logger.info(
        f"📊 {agent_label} usage: {usage_metrics.tokensUsed} tokens, "
        f"model={usage_metrics.modelName}, cost={usage_metrics.costUsd}"
    )
    return tool_calls, usage_metrics


def capture_agent_prompts(agent, task_prompt: str) -> tuple[str | None, str]:
    """Return ``(system_prompt, task_prompt)`` for observability persistence.

    ``Agent.instructions`` is typed ``str | Callable[..., str] | None`` by the SDK
    but project agents always set a str. The isinstance narrow keeps prompt
    capture safe if anyone later swaps to a dynamic callable, and logs the
    skip at DEBUG so a regression in observability is visible.
    """
    instructions = agent.instructions
    if not isinstance(instructions, str) and instructions is not None:
        logger.debug(
            "%s.instructions is callable, not str — skipping prompt capture for observability",
            type(agent).__name__,
        )
    system_prompt = instructions if isinstance(instructions, str) else None
    return system_prompt, task_prompt
