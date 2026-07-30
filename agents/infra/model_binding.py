"""Per-phase model binding — the app declares intent, the gateway resolves it.

A phase says *what tier of work it needs* (``research-tier``, ``decision-tier``);
the LiteLLM gateway maps that intent to a concrete model, timeout and retry
policy. Rebinding a phase to a different model is then a gateway config commit,
not an app rebuild.

``sdk_model`` is an ``OpenAIChatCompletionsModel`` when a gateway is configured.
The Chat Completions surface is deliberate: the SDK defaults to ``/v1/responses``,
which the gateway's OpenAI-compatible routes do not serve. Without a gateway
(local dev) it degrades to today's behaviour — the bare model string, resolved
by the SDK's own client against the provider.

Each agent presents its own virtual key, read from ``LLM_GATEWAY_KEY_<AGENT>``.
That is what makes the gateway's budget ceilings and rate limits per-agent and
lets one agent be revoked without touching the others.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from enum import StrEnum

import httpx
from agents import ModelSettings, OpenAIChatCompletionsModel
from agents.model_settings import Reasoning
from openai import AsyncOpenAI

from config import config
from infra.gateway_usage import record_gateway_response

logger = logging.getLogger(__name__)


class Phase(StrEnum):
    """A cycle phase that issues LLM calls."""

    RESEARCH = "research"
    DECISION = "decision"


_INTENT_CONFIG_KEY: dict[Phase, str] = {
    Phase.RESEARCH: "MODEL_INTENT_RESEARCH",
    Phase.DECISION: "MODEL_INTENT_DECISION",
}

_EFFORT_CONFIG_KEY: dict[Phase, str] = {
    Phase.RESEARCH: "RESEARCH_REASONING_EFFORT",
    Phase.DECISION: "DECISION_REASONING_EFFORT",
}


@dataclass(frozen=True)
class PhaseBinding:
    """Everything one phase needs to issue an LLM call.

    ``intent`` is what the app asks for; the gateway decides what serves it.
    ``model_label`` is the string persisted with the run's usage metrics — the
    intent on the gateway path, the concrete model otherwise.
    """

    phase: Phase
    intent: str
    reasoning_effort: str
    tags: tuple[str, ...]
    model_label: str
    sdk_model: OpenAIChatCompletionsModel | str
    via_gateway: bool
    model_settings: ModelSettings = field(repr=False)


def gateway_enabled() -> bool:
    """True when both a gateway URL and a virtual key are configured."""
    return bool(config.LLM_GATEWAY_BASE_URL and config.LLM_GATEWAY_API_KEY)


_gateway_clients: dict[tuple[str, str], AsyncOpenAI] = {}

_KEY_ENV_PREFIX = "LLM_GATEWAY_KEY_"
_ENV_NAME_SAFE = re.compile(r"[^A-Z0-9]+")


def _agent_key_env_var(agent_name: str) -> str:
    """Env var holding one agent's virtual key, e.g. ``Warren B.`` → ``..._WARREN_B``.

    Agent names come from the database and are display strings, so they are
    normalised rather than trusted: without this a rename to ``"Warren B."``
    would silently miss its key and fall back to the shared one, quietly
    un-budgeting that agent.
    """
    slug = _ENV_NAME_SAFE.sub("_", agent_name.upper()).strip("_")
    return f"{_KEY_ENV_PREFIX}{slug}"


def _virtual_key_for(agent_name: str) -> str:
    """This agent's virtual key, falling back to the fleet key.

    Per-agent keys are what make the gateway's budget caps and revocation
    per-agent: a shared credential turns every cap into a fleet cap and every
    revocation into a fleet outage. The fallback exists so adding an agent to
    the roster does not take it offline before an operator mints its key —
    it stays budgeted, just against the shared ceiling.
    """
    dedicated = os.getenv(_agent_key_env_var(agent_name), "")
    if dedicated:
        return dedicated
    logger.debug(
        "No dedicated gateway key for %r (%s unset); using the shared key",
        agent_name,
        _agent_key_env_var(agent_name),
    )
    return config.LLM_GATEWAY_API_KEY


def _gateway_client(api_key: str) -> AsyncOpenAI:
    """One client per (base_url, key) — that is, one per agent.

    Keyed by credential rather than by phase: an agent's phases share a
    connection pool, and two agents never share a client, so a per-agent key
    cannot leak across agents via a cached client.

    The httpx client is built here rather than left to the SDK so the response
    hook that reads the gateway's cost headers can be attached; see
    ``infra.gateway_usage`` for why the headers are the only cost source once a
    phase names an intent instead of a model.
    """
    identity = (config.LLM_GATEWAY_BASE_URL, api_key)
    client = _gateway_clients.get(identity)
    if client is None:
        client = AsyncOpenAI(
            base_url=identity[0],
            api_key=identity[1],
            http_client=httpx.AsyncClient(event_hooks={"response": [record_gateway_response]}),
        )
        _gateway_clients[identity] = client
    return client


def _build_model_settings(
    reasoning_effort: str, tags: tuple[str, ...], via_gateway: bool
) -> ModelSettings:
    """Explicit reasoning effort plus the spend tags the gateway attributes to.

    Both fields are for the gateway alone, and off it the provider rejects the
    request outright rather than ignoring them, so the direct path sends neither:

    * ``tags`` is a LiteLLM extension — 400 ``unknown_parameter``. It goes in
      ``extra_body`` under the top-level key because that is the only shape the
      proxy reads: ``add_request_tag_to_metadata`` checks the ``x-litellm-tags``
      header and ``data["tags"]`` and nothing else, so tags sent anywhere else
      are dropped before the spend row is written.
    * ``reasoning.effort`` exists only on reasoning models — 400
      ``unsupported_parameter``. Every gateway deployment is one; ``OPENAI_MODEL``,
      which serves the direct path, need not be.
    """
    if not via_gateway:
        return ModelSettings()
    return ModelSettings(
        reasoning=Reasoning(effort=reasoning_effort),  # type: ignore[arg-type]
        extra_body={"tags": list(tags)},
    )


def resolve_phase_binding(
    phase: Phase,
    agent_name: str,
    model_override: str | None = None,
) -> PhaseBinding:
    """Resolve intent, reasoning effort, spend tags and the SDK model for a phase.

    ``model_override`` names a concrete model instead of the phase intent. It
    still routes through the gateway when one is configured, so an override
    stays budgeted, logged and rate-limited like every other call.
    """
    intent: str = getattr(config, _INTENT_CONFIG_KEY[phase])
    reasoning_effort: str = getattr(config, _EFFORT_CONFIG_KEY[phase])
    tags = (f"phase:{phase.value}", f"agent:{agent_name.lower()}")

    via_gateway = gateway_enabled()
    if via_gateway:
        model_label = model_override if model_override is not None else intent
        sdk_model: OpenAIChatCompletionsModel | str = OpenAIChatCompletionsModel(
            model=model_label, openai_client=_gateway_client(_virtual_key_for(agent_name))
        )
    else:
        # No gateway: an intent alias means nothing to the provider, so a phase
        # that didn't name a concrete model falls back to the global default.
        model_label = model_override if model_override is not None else config.OPENAI_MODEL
        sdk_model = model_label
        logger.debug(
            "LLM gateway not configured; %s phase binding to %r directly", phase.value, model_label
        )

    return PhaseBinding(
        phase=phase,
        intent=intent,
        reasoning_effort=reasoning_effort,
        tags=tags,
        model_label=model_label,
        sdk_model=sdk_model,
        via_gateway=via_gateway,
        model_settings=_build_model_settings(reasoning_effort, tags, via_gateway),
    )
