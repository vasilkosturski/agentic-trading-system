"""Per-phase model binding: intent resolution, reasoning effort, gateway wiring.

These tests pin the contract the LiteLLM gateway depends on:

* each phase declares its own *intent* (a gateway alias), not one global model name
* reasoning effort is explicit per phase instead of implied by a bare model string
* every request carries phase/agent tags the gateway can attribute spend to
* when a gateway is configured the SDK talks Chat Completions, never the
  default Responses surface (the gateway does not serve /v1/responses)
"""

import pytest
from agents import OpenAIChatCompletionsModel, OpenAIResponsesModel

from config import config
from infra.gateway_usage import record_gateway_response
from infra.model_binding import Phase, gateway_enabled, resolve_phase_binding


@pytest.fixture
def gateway_configured(monkeypatch):
    """Point the app at a gateway with a virtual key, as in staging/production."""
    monkeypatch.setattr(config, "LLM_GATEWAY_BASE_URL", "http://litellm-service:4000")
    monkeypatch.setattr(config, "LLM_GATEWAY_API_KEY", "sk-virtual-warren")
    return config


@pytest.fixture
def gateway_absent(monkeypatch):
    """Local dev: no gateway, agents call the provider directly."""
    monkeypatch.setattr(config, "LLM_GATEWAY_BASE_URL", "")
    monkeypatch.setattr(config, "LLM_GATEWAY_API_KEY", "")
    return config


class TestPhaseBinding:
    def test_research_and_decision_resolve_distinct_intents(self):
        research = resolve_phase_binding(Phase.RESEARCH, "Warren")
        decision = resolve_phase_binding(Phase.DECISION, "Warren")

        assert research.intent != decision.intent, (
            "research and decision must declare different tiers of work; a single "
            "global model name is exactly what this change removes"
        )
        assert research.intent == config.MODEL_INTENT_RESEARCH
        assert decision.intent == config.MODEL_INTENT_DECISION

    def test_reasoning_effort_is_explicit_per_phase(self, gateway_configured):
        research = resolve_phase_binding(Phase.RESEARCH, "Warren")
        decision = resolve_phase_binding(Phase.DECISION, "Warren")

        assert research.reasoning_effort == config.RESEARCH_REASONING_EFFORT
        assert decision.reasoning_effort == config.DECISION_REASONING_EFFORT
        assert research.model_settings.reasoning is not None
        assert research.model_settings.reasoning.effort == research.reasoning_effort

    def test_tags_carry_phase_and_agent(self):
        binding = resolve_phase_binding(Phase.DECISION, "Warren")

        assert "phase:decision" in binding.tags
        assert "agent:warren" in binding.tags

    def test_tags_reach_the_only_body_field_litellm_reads(self, gateway_configured):
        binding = resolve_phase_binding(Phase.RESEARCH, "Cathie")

        # LiteLLM reads request tags off the top-level ``tags`` body field
        # (litellm_pre_call_utils.add_request_tag_to_metadata); anything nested
        # deeper never reaches the spend table's request_tags column.
        extra_body = binding.model_settings.extra_body
        assert extra_body is not None
        assert extra_body["tags"] == list(binding.tags)

    def test_no_gateway_sends_neither_tags_nor_reasoning(self, gateway_absent):
        """Off the gateway the request carries neither gateway-only field.

        Both are rejected outright by the provider: ``tags`` is a LiteLLM
        extension (400 ``unknown_parameter``) and ``reasoning.effort`` exists
        only on reasoning models, which ``OPENAI_MODEL`` need not be
        (400 ``unsupported_parameter``).
        """
        binding = resolve_phase_binding(Phase.RESEARCH, "Cathie")

        assert not (binding.model_settings.extra_body or {})
        assert binding.model_settings.reasoning is None
        assert binding.tags, "the binding still records them for local telemetry"
        assert binding.reasoning_effort, "and the effort the gateway would have used"


class TestGatewayWiring:
    def test_gateway_binding_uses_chat_completions_surface(self, gateway_configured):
        binding = resolve_phase_binding(Phase.RESEARCH, "Warren")

        assert gateway_enabled() is True
        assert binding.via_gateway is True
        assert isinstance(binding.sdk_model, OpenAIChatCompletionsModel), (
            "the gateway does not serve /v1/responses; the SDK's default surface "
            "would 404 against it"
        )
        assert not isinstance(binding.sdk_model, OpenAIResponsesModel)

    def test_gateway_binding_targets_gateway_with_virtual_key(self, gateway_configured):
        binding = resolve_phase_binding(Phase.DECISION, "Warren")

        client = binding.sdk_model._client  # the AsyncOpenAI the SDK was handed
        assert str(client.base_url).rstrip("/") == config.LLM_GATEWAY_BASE_URL.rstrip("/")
        assert client.api_key == config.LLM_GATEWAY_API_KEY
        assert binding.sdk_model.model == config.MODEL_INTENT_DECISION
        assert binding.model_label == config.MODEL_INTENT_DECISION

    def test_gateway_absent_falls_back_to_direct_model_string(self, gateway_absent):
        binding = resolve_phase_binding(Phase.RESEARCH, "Warren")

        assert gateway_enabled() is False
        assert binding.via_gateway is False
        assert binding.sdk_model == config.OPENAI_MODEL, (
            "without a gateway the intent cannot be resolved, so local dev falls "
            "back to the concrete model the SDK can reach directly"
        )
        assert binding.model_label == config.OPENAI_MODEL

    def test_explicit_override_still_routes_through_the_gateway(self, gateway_configured):
        binding = resolve_phase_binding(Phase.RESEARCH, "Warren", model_override="gpt-4o")

        assert isinstance(binding.sdk_model, OpenAIChatCompletionsModel)
        assert binding.sdk_model.model == "gpt-4o"
        assert binding.model_label == "gpt-4o"

    def test_override_without_gateway_is_the_bare_string(self, gateway_absent):
        binding = resolve_phase_binding(Phase.DECISION, "Warren", model_override="gpt-4o")

        assert binding.sdk_model == "gpt-4o"
        assert binding.model_label == "gpt-4o"

    def test_gateway_client_is_reused_for_one_agent(self, gateway_configured):
        first = resolve_phase_binding(Phase.RESEARCH, "Warren")
        second = resolve_phase_binding(Phase.DECISION, "Warren")

        assert first.sdk_model._client is second.sdk_model._client, (
            "one connection pool per gateway identity; a new client per phase "
            "per cycle buys nothing"
        )


class TestPerAgentCredentials:
    """One virtual key per agent — the whole point of the credential change.

    A single shared key would make every budget cap a *fleet* cap and every
    revocation a fleet outage. These tests pin the isolation the security
    requirement asks for: revoking one agent affects only that agent.
    """

    def test_each_agent_presents_its_own_virtual_key(self, monkeypatch):
        monkeypatch.setattr(config, "LLM_GATEWAY_BASE_URL", "http://litellm-service:4000")
        monkeypatch.setattr(config, "LLM_GATEWAY_API_KEY", "sk-fleet-fallback")
        monkeypatch.setenv("LLM_GATEWAY_KEY_WARREN", "sk-virtual-warren")
        monkeypatch.setenv("LLM_GATEWAY_KEY_CATHIE", "sk-virtual-cathie")

        warren = resolve_phase_binding(Phase.RESEARCH, "Warren")
        cathie = resolve_phase_binding(Phase.RESEARCH, "Cathie")

        assert warren.sdk_model._client.api_key == "sk-virtual-warren"
        assert cathie.sdk_model._client.api_key == "sk-virtual-cathie", (
            "a shared key means Cathie's spend counts against Warren's budget and "
            "revoking Warren's key takes the whole fleet down"
        )

    def test_agents_without_a_dedicated_key_fall_back_to_the_shared_one(self, monkeypatch):
        """A newly added agent must not lose LLM access before its key exists.

        Falling back keeps the cut-over boring, which is the parity gate: the
        agent still runs, still budgeted, just against the fleet key until an
        operator mints its own.
        """
        monkeypatch.setattr(config, "LLM_GATEWAY_BASE_URL", "http://litellm-service:4000")
        monkeypatch.setattr(config, "LLM_GATEWAY_API_KEY", "sk-fleet-fallback")
        monkeypatch.delenv("LLM_GATEWAY_KEY_NEWCOMER", raising=False)

        binding = resolve_phase_binding(Phase.DECISION, "Newcomer")

        assert binding.sdk_model._client.api_key == "sk-fleet-fallback"

    def test_agent_name_is_normalised_into_the_env_var_name(self, monkeypatch):
        """Agent names come from the DB and are display strings, not identifiers.

        Without normalisation a roster rename to "Warren B." would silently drop
        the agent back to the fleet key and quietly un-budget it.
        """
        monkeypatch.setattr(config, "LLM_GATEWAY_BASE_URL", "http://litellm-service:4000")
        monkeypatch.setattr(config, "LLM_GATEWAY_API_KEY", "sk-fleet-fallback")
        monkeypatch.setenv("LLM_GATEWAY_KEY_WARREN_B", "sk-virtual-warren-b")

        binding = resolve_phase_binding(Phase.RESEARCH, "Warren B.")

        assert binding.sdk_model._client.api_key == "sk-virtual-warren-b"

    def test_one_client_per_agent_not_per_phase(self, monkeypatch):
        monkeypatch.setattr(config, "LLM_GATEWAY_BASE_URL", "http://litellm-service:4000")
        monkeypatch.setattr(config, "LLM_GATEWAY_API_KEY", "sk-fleet-fallback")
        monkeypatch.setenv("LLM_GATEWAY_KEY_WARREN", "sk-virtual-warren")
        monkeypatch.setenv("LLM_GATEWAY_KEY_CATHIE", "sk-virtual-cathie")

        warren_research = resolve_phase_binding(Phase.RESEARCH, "Warren")
        warren_decision = resolve_phase_binding(Phase.DECISION, "Warren")
        cathie = resolve_phase_binding(Phase.RESEARCH, "Cathie")

        assert warren_research.sdk_model._client is warren_decision.sdk_model._client
        assert warren_research.sdk_model._client is not cathie.sdk_model._client

    def test_per_agent_clients_still_capture_cost_headers(self, monkeypatch):
        """The cost hook is attached per client, so a new agent must not silently
        lose cost attribution."""
        monkeypatch.setattr(config, "LLM_GATEWAY_BASE_URL", "http://litellm-service:4000")
        monkeypatch.setattr(config, "LLM_GATEWAY_API_KEY", "sk-fleet-fallback")
        monkeypatch.setenv("LLM_GATEWAY_KEY_CATHIE", "sk-virtual-cathie")

        binding = resolve_phase_binding(Phase.RESEARCH, "Cathie")

        hooks = binding.sdk_model._client._client.event_hooks["response"]
        assert record_gateway_response in hooks

    def test_gateway_client_captures_cost_headers(self, gateway_configured):
        """The SDK discards response headers, so the gateway's per-call cost and
        concrete model name are only reachable via an httpx event hook."""
        binding = resolve_phase_binding(Phase.RESEARCH, "Warren")

        hooks = binding.sdk_model._client._client.event_hooks["response"]
        assert record_gateway_response in hooks, (
            "without this hook the intent alias has no price: MODEL_PRICING has "
            "no 'research-tier' entry and costUsd would be None on every run"
        )
