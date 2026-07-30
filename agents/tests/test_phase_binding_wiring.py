"""Both agent factories bind through the per-phase seam, not a global model name.

The gateway can only attribute spend and enforce per-phase policy if the
``Agent`` the SDK runs actually carries the phase's model, reasoning effort and
tags. These tests assert that on the constructed agents rather than on the
binding helper, which ``test_model_binding.py`` covers on its own.
"""

import pytest
from agents import OpenAIChatCompletionsModel

from ai_agents.decision_maker import create_decision_maker_agent
from ai_agents.market_analyst import create_market_analyst_agent
from config import config
from infra.model_binding import Phase


@pytest.fixture
def gateway_configured(monkeypatch):
    monkeypatch.setattr(config, "LLM_GATEWAY_BASE_URL", "http://litellm-service:4000")
    monkeypatch.setattr(config, "LLM_GATEWAY_API_KEY", "sk-virtual-warren")
    return config


@pytest.fixture
def gateway_absent(monkeypatch):
    monkeypatch.setattr(config, "LLM_GATEWAY_BASE_URL", "")
    monkeypatch.setattr(config, "LLM_GATEWAY_API_KEY", "")
    return config


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_prompt_fetch")
class TestMarketAnalystBinding:
    async def test_binds_research_intent_over_chat_completions(
        self, sample_agent_name, mock_mcp_pool, gateway_configured
    ):
        agent = await create_market_analyst_agent(
            agent_name=sample_agent_name, mcp_pool=mock_mcp_pool
        )

        assert isinstance(agent.model, OpenAIChatCompletionsModel), (
            "the gateway serves /v1/chat/completions only; the SDK's default "
            "Responses surface would 404"
        )
        assert agent.model.model == config.MODEL_INTENT_RESEARCH

    async def test_carries_research_effort_and_phase_tags(
        self, sample_agent_name, mock_mcp_pool, gateway_configured
    ):
        agent = await create_market_analyst_agent(
            agent_name=sample_agent_name, mcp_pool=mock_mcp_pool
        )

        assert agent.model_settings.reasoning is not None
        assert agent.model_settings.reasoning.effort == config.RESEARCH_REASONING_EFFORT
        tags = agent.model_settings.extra_body["tags"]
        assert f"phase:{Phase.RESEARCH.value}" in tags
        assert f"agent:{sample_agent_name.lower()}" in tags

    async def test_without_gateway_falls_back_to_the_global_model(
        self, sample_agent_name, mock_mcp_pool, gateway_absent
    ):
        agent = await create_market_analyst_agent(
            agent_name=sample_agent_name, mcp_pool=mock_mcp_pool
        )

        assert agent.model == config.OPENAI_MODEL

    async def test_explicit_model_name_is_still_honoured(
        self, sample_agent_name, mock_mcp_pool, sample_model_name, gateway_absent
    ):
        agent = await create_market_analyst_agent(
            agent_name=sample_agent_name,
            mcp_pool=mock_mcp_pool,
            model_name=sample_model_name,
        )

        assert agent.model == sample_model_name


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_prompt_fetch")
class TestDecisionMakerBinding:
    async def test_binds_decision_intent_over_chat_completions(
        self, sample_agent_name, sample_agent_id, mock_mcp_pool, gateway_configured
    ):
        agent = await create_decision_maker_agent(
            agent_name=sample_agent_name, agent_id=sample_agent_id, mcp_pool=mock_mcp_pool
        )

        assert isinstance(agent.model, OpenAIChatCompletionsModel)
        assert agent.model.model == config.MODEL_INTENT_DECISION

    async def test_carries_decision_effort_and_phase_tags(
        self, sample_agent_name, sample_agent_id, mock_mcp_pool, gateway_configured
    ):
        agent = await create_decision_maker_agent(
            agent_name=sample_agent_name, agent_id=sample_agent_id, mcp_pool=mock_mcp_pool
        )

        assert agent.model_settings.reasoning is not None
        assert agent.model_settings.reasoning.effort == config.DECISION_REASONING_EFFORT
        tags = agent.model_settings.extra_body["tags"]
        assert f"phase:{Phase.DECISION.value}" in tags
        assert f"agent:{sample_agent_name.lower()}" in tags

    async def test_decision_and_research_do_not_share_one_binding(
        self, sample_agent_name, sample_agent_id, mock_mcp_pool, gateway_configured
    ):
        analyst = await create_market_analyst_agent(
            agent_name=sample_agent_name, mcp_pool=mock_mcp_pool
        )
        maker = await create_decision_maker_agent(
            agent_name=sample_agent_name, agent_id=sample_agent_id, mcp_pool=mock_mcp_pool
        )

        assert analyst.model.model != maker.model.model
        assert analyst.model_settings.extra_body["tags"] != maker.model_settings.extra_body["tags"]
