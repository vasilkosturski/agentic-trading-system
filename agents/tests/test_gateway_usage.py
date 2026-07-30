"""Cost capture from the gateway's own response headers.

The proxy returns ``x-litellm-response-cost`` and ``x-litellm-model-name``
(the concrete deployment, not the intent alias) on every chat-completion. The
Agents SDK calls ``chat.completions.create()`` and throws the headers away, so
capture happens one layer down on the httpx client and is read back per phase.
"""

import asyncio

import httpx
import pytest

from infra.gateway_usage import collect_gateway_usage, record_gateway_response


def _response(headers: dict[str, str]) -> httpx.Response:
    return httpx.Response(200, headers=headers, json={})


class TestCollector:
    async def test_records_cost_and_concrete_model(self):
        with collect_gateway_usage() as usage:
            await record_gateway_response(
                _response(
                    {
                        "x-litellm-response-cost": "0.00123",
                        "x-litellm-model-name": "gpt-5-mini",
                    }
                )
            )

        assert usage.responses == 1
        assert usage.cost_usd == pytest.approx(0.00123)
        assert usage.model_names == ["gpt-5-mini"]

    async def test_sums_cost_across_the_tool_loop(self):
        """One Runner.run makes one request per turn; the phase's cost is the sum."""
        with collect_gateway_usage() as usage:
            for cost in ("0.001", "0.002", "0.004"):
                await record_gateway_response(
                    _response({"x-litellm-response-cost": cost, "x-litellm-model-name": "gpt-5"})
                )

        assert usage.responses == 3
        assert usage.cost_usd == pytest.approx(0.007)
        assert usage.model_names == ["gpt-5"], "repeat models are recorded once"

    async def test_records_two_deployments_as_two_models(self):
        with collect_gateway_usage() as usage:
            await record_gateway_response(
                _response({"x-litellm-response-cost": "0.001", "x-litellm-model-name": "gpt-5"})
            )
            await record_gateway_response(
                _response(
                    {"x-litellm-response-cost": "0.002", "x-litellm-model-name": "gpt-5-mini"}
                )
            )

        assert usage.model_names == ["gpt-5", "gpt-5-mini"]

    async def test_a_response_without_cost_headers_is_not_counted(self):
        """Non-LLM traffic on the same client (e.g. /health) must not inflate the
        response count, or the caller would trust a zero cost as real."""
        with collect_gateway_usage() as usage:
            await record_gateway_response(_response({}))

        assert usage.responses == 0
        assert usage.cost_usd == 0.0

    async def test_an_unparseable_cost_counts_the_call_but_not_the_cost(self):
        """LiteLLM stringifies the cost, so a null cost arrives as "None"."""
        with collect_gateway_usage() as usage:
            await record_gateway_response(
                _response({"x-litellm-response-cost": "None", "x-litellm-model-name": "gpt-5"})
            )

        assert usage.responses == 1
        assert usage.cost_usd is None, "an unpriced call must not read as a free call"
        assert usage.model_names == ["gpt-5"]

    async def test_recording_outside_a_collector_is_a_no_op(self):
        """The client is shared; a request made outside a phase must not crash."""
        await record_gateway_response(
            _response({"x-litellm-response-cost": "0.001", "x-litellm-model-name": "gpt-5"})
        )

    async def test_concurrent_phases_do_not_share_a_collector(self):
        """Four agents run in one gather; each must see only its own spend."""

        async def phase(cost: str, model: str):
            with collect_gateway_usage() as usage:
                await record_gateway_response(
                    _response({"x-litellm-response-cost": cost, "x-litellm-model-name": model})
                )
                await asyncio.sleep(0)  # interleave with the other tasks
                await record_gateway_response(
                    _response({"x-litellm-response-cost": cost, "x-litellm-model-name": model})
                )
            return usage

        warren, cathie = await asyncio.gather(phase("0.01", "gpt-5"), phase("0.50", "gpt-5-mini"))

        assert warren.cost_usd == pytest.approx(0.02)
        assert cathie.cost_usd == pytest.approx(1.0)
