"""Usage metrics when the gateway, not the local pricing table, knows the price.

On the gateway path the phase names an intent (``research-tier``), so
``MODEL_PRICING`` cannot price it and the SDK's Chat Completions path reports no
model name of its own. The gateway's response headers carry both. These tests
pin that the gateway wins when it reported, and that nothing changes for the
no-gateway path.
"""

from agents import Usage

from infra.gateway_usage import GatewayUsage
from phase_runner._telemetry import extract_usage_metrics


def _usage(input_tokens: int = 1000, output_tokens: int = 500) -> Usage:
    return Usage(
        requests=1,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
    )


def _reported(cost: str, model: str, calls: int = 1) -> GatewayUsage:
    usage = GatewayUsage()
    for _ in range(calls):
        usage.record(cost, model)
    return usage


class TestGatewayReportedCost:
    def test_gateway_cost_is_used_verbatim(self):
        metrics = extract_usage_metrics(
            _usage(),
            model_name="research-tier",
            gateway_usage=_reported("0.00042", "gpt-5-mini"),
        )

        assert metrics.costUsd == 0.00042

    def test_gateway_concrete_model_replaces_the_intent_alias(self):
        """Persisting 'research-tier' would make the model column useless for
        answering "which model actually served this run?"."""
        metrics = extract_usage_metrics(
            _usage(),
            model_name="research-tier",
            gateway_usage=_reported("0.00042", "gpt-5-mini"),
        )

        assert metrics.modelName == "gpt-5-mini"

    def test_multiple_deployments_keep_the_intent_label_and_sum_cost(self):
        usage = GatewayUsage()
        usage.record("0.001", "gpt-5-mini")
        usage.record("0.002", "gpt-5")

        metrics = extract_usage_metrics(_usage(), model_name="research-tier", gateway_usage=usage)

        assert metrics.costUsd == 0.003
        assert metrics.modelName == "research-tier", (
            "two deployments served this phase; naming one of them would be a lie"
        )

    def test_no_gateway_usage_falls_back_to_the_local_pricing_table(self):
        metrics = extract_usage_metrics(_usage(), model_name="gpt-5-mini", gateway_usage=None)

        assert metrics.modelName == "gpt-5-mini"
        assert metrics.costUsd is not None and metrics.costUsd > 0

    def test_an_intent_alias_with_no_gateway_report_yields_no_cost(self):
        """The honest outcome: MODEL_PRICING has no alias entry, so rather than
        guess, costUsd stays None as it already does for unknown models."""
        metrics = extract_usage_metrics(
            _usage(),
            model_name="research-tier",
            gateway_usage=GatewayUsage(),
        )

        assert metrics.costUsd is None

    def test_an_unpriced_gateway_call_does_not_fall_back_to_local_pricing(self):
        """A concrete model plus an unparseable cost is the one case where both
        sources exist. The gateway is the authority on the gateway path — a local
        estimate silently mixed into the same column would be unaggregatable."""
        usage = GatewayUsage()
        usage.record("None", "gpt-5-mini")

        metrics = extract_usage_metrics(_usage(), model_name="research-tier", gateway_usage=usage)

        assert metrics.costUsd is None
        assert metrics.modelName == "gpt-5-mini"
