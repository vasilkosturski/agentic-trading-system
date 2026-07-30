"""SDK trace export must not depend on a provider key the pod no longer holds.

The Agents SDK ships traces to api.openai.com authenticated with
``OPENAI_API_KEY``. After the gateway cut-over the agent pod has no provider
key, so the exporter would warn on every span and never deliver. Disable
tracing explicitly in that case rather than letting it fail quietly.
"""

from unittest.mock import patch

import pytest

from config import config
from infra.tracing_setup import configure_tracing


@pytest.fixture
def gateway_only(monkeypatch):
    monkeypatch.setattr(config, "LLM_GATEWAY_BASE_URL", "http://litellm-service:4000")
    monkeypatch.setattr(config, "LLM_GATEWAY_API_KEY", "sk-virtual-warren")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    return config


@pytest.fixture
def provider_key_present(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-provider")
    return config


def test_tracing_disabled_when_no_provider_key(gateway_only):
    with patch("infra.tracing_setup.set_tracing_disabled") as p_disable:
        enabled = configure_tracing()

    assert enabled is False
    p_disable.assert_called_once_with(True)


def test_tracing_left_enabled_when_provider_key_present(provider_key_present):
    with patch("infra.tracing_setup.set_tracing_disabled") as p_disable:
        enabled = configure_tracing()

    assert enabled is True
    p_disable.assert_not_called()


def test_explicit_tracing_key_keeps_tracing_on(gateway_only, monkeypatch):
    """A dedicated trace-ingest key lets tracing survive the cut-over without
    reintroducing a provider key into the LLM call path."""
    monkeypatch.setattr(config, "OPENAI_TRACING_API_KEY", "sk-tracing-only")

    with (
        patch("infra.tracing_setup.set_tracing_disabled") as p_disable,
        patch("infra.tracing_setup.set_tracing_export_api_key") as p_key,
    ):
        enabled = configure_tracing()

    assert enabled is True
    p_disable.assert_not_called()
    p_key.assert_called_once_with("sk-tracing-only")
