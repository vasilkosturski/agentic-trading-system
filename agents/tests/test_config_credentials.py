"""Config credential validation across the gateway cut-over.

After the cut-over the agent pod holds a gateway virtual key and no provider
key, so requiring ``OPENAI_API_KEY`` unconditionally would make the deployed
configuration unstartable. Exactly one credential path must be present.
"""

import pytest

from config import Config


def _env(**overrides) -> dict[str, str]:
    base = {
        "OPENAI_API_KEY": "",
        "LLM_GATEWAY_BASE_URL": "",
        "LLM_GATEWAY_API_KEY": "",
        "BRAVE_API_KEY": "brave-key",
    }
    base.update(overrides)
    return base


def _build(monkeypatch, env: dict[str, str]) -> Config:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    # Class attributes are bound at import time from os.getenv; rebind them so
    # the constructor validates the env under test rather than import-time env.
    for key, value in env.items():
        if hasattr(Config, key):
            monkeypatch.setattr(Config, key, value)
    return Config()


class TestCredentialValidation:
    def test_gateway_key_alone_is_sufficient(self, monkeypatch):
        cfg = _build(
            monkeypatch,
            _env(
                LLM_GATEWAY_BASE_URL="http://litellm-service:4000",
                LLM_GATEWAY_API_KEY="sk-virtual-warren",
            ),
        )

        assert cfg.LLM_GATEWAY_API_KEY == "sk-virtual-warren"
        assert cfg.OPENAI_API_KEY == "", (
            "the deployed agent pod must start with no provider key at all — "
            "that is the credential-blast-radius win"
        )

    def test_provider_key_alone_is_sufficient(self, monkeypatch):
        cfg = _build(monkeypatch, _env(OPENAI_API_KEY="sk-provider"))

        assert cfg.OPENAI_API_KEY == "sk-provider"

    def test_no_credential_at_all_is_rejected(self, monkeypatch):
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            _build(monkeypatch, _env())

    def test_gateway_url_without_a_key_is_rejected(self, monkeypatch):
        """A URL with no virtual key would send unauthenticated requests that
        the gateway rejects at runtime; fail at startup instead."""
        with pytest.raises(ValueError, match="LLM_GATEWAY_API_KEY"):
            _build(monkeypatch, _env(LLM_GATEWAY_BASE_URL="http://litellm-service:4000"))

    def test_gateway_key_without_a_url_is_rejected(self, monkeypatch):
        with pytest.raises(ValueError, match="LLM_GATEWAY_BASE_URL"):
            _build(monkeypatch, _env(LLM_GATEWAY_API_KEY="sk-virtual-warren"))

    def test_brave_key_is_still_required(self, monkeypatch):
        with pytest.raises(ValueError, match="BRAVE_API_KEY"):
            _build(monkeypatch, _env(OPENAI_API_KEY="sk-provider", BRAVE_API_KEY=""))
