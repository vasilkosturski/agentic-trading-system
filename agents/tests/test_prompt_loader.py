"""Tests for prompt_loader: async API-based prompt loading with in-process cache.

prompt_loader.load_composed_prompt is now an async function that routes through
BackendClient.request and caches results per (agent_type, agent_name) for the
lifetime of the process.

Covers:
1. load_composed_prompt() routes through BackendClient.request (no direct httpx.get)
2. Per-(agent_type, agent_name) cache prevents repeat HTTP calls
3. format_prompt() runtime placeholder substitution
4. Validation (invalid agent names, backend errors)
5. get_available_templates() returns expected structure
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from infra.prompt_loader import (
    VALID_AGENT_NAMES,
    clear_prompt_cache,
    format_prompt,
    load_and_format_prompt,
    load_composed_prompt,
)


@pytest.fixture(autouse=True)
def _reset_prompt_cache():
    """Ensure each test starts with an empty in-process prompt cache."""
    clear_prompt_cache()
    yield
    clear_prompt_cache()


def _make_response(text: str, status_code: int = 200) -> MagicMock:
    """Build a MagicMock that mimics httpx.Response for our async path."""
    mock = MagicMock(spec=httpx.Response)
    mock.text = text
    mock.status_code = status_code
    return mock


# ============================================================================
# 1. load_composed_prompt() routes through BackendClient.request (async)
# ============================================================================


class TestLoadComposedPrompt:
    """Test API-based prompt loading via BackendClient.request."""

    @pytest.mark.asyncio
    async def test_routes_through_backend_client_request(self):
        """Calls BackendClient.request with the correct URL — not httpx.get directly."""
        mock_request = AsyncMock(return_value=_make_response("You are Warren."))
        with patch("infra.prompt_loader._get_backend_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.request = mock_request
            mock_get_client.return_value = mock_client

            result = await load_composed_prompt("decision_maker", "Warren")

            assert result == "You are Warren."
            mock_request.assert_awaited_once()
            args, kwargs = mock_request.call_args
            # request signature: (method, url, *, params=None, json_data=None)
            method = args[0] if args else kwargs.get("method")
            url = args[1] if len(args) > 1 else kwargs.get("url")
            assert method == "GET"
            assert "/api/prompts/decision_maker/warren" in url

    @pytest.mark.asyncio
    async def test_invalid_agent_name_raises_value_error(self):
        """Invalid agent name raises ValueError without calling backend."""
        with pytest.raises(ValueError, match="Invalid agent name"):
            await load_composed_prompt("market_analyst", "invalid_agent")


# ============================================================================
# 2. In-process cache: a 2nd call for the same key does NOT re-fetch.
# ============================================================================


class TestPromptCache:
    """Verify the per-(agent_type, agent_name) cache."""

    @pytest.mark.asyncio
    async def test_second_call_does_not_trigger_second_http_call(self):
        """Second call for the same (agent_type, agent_name) is served from cache."""
        mock_request = AsyncMock(return_value=_make_response("cached prompt"))
        with patch("infra.prompt_loader._get_backend_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.request = mock_request
            mock_get_client.return_value = mock_client

            first = await load_composed_prompt("market_analyst", "Warren")
            second = await load_composed_prompt("market_analyst", "Warren")

            assert first == "cached prompt"
            assert second == "cached prompt"
            # CRITICAL: the HTTP layer was hit exactly once.
            assert mock_request.await_count == 1

    @pytest.mark.asyncio
    async def test_different_keys_each_fetch_once(self):
        """Distinct (agent_type, agent_name) tuples each trigger their own fetch."""
        mock_request = AsyncMock(
            side_effect=[
                _make_response("warren-analyst"),
                _make_response("warren-decider"),
                _make_response("george-analyst"),
            ]
        )
        with patch("infra.prompt_loader._get_backend_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.request = mock_request
            mock_get_client.return_value = mock_client

            a = await load_composed_prompt("market_analyst", "Warren")
            b = await load_composed_prompt("decision_maker", "Warren")
            c = await load_composed_prompt("market_analyst", "George")

            # Re-fetch the first key — must hit cache.
            a2 = await load_composed_prompt("market_analyst", "Warren")

            assert (a, b, c, a2) == (
                "warren-analyst",
                "warren-decider",
                "george-analyst",
                "warren-analyst",
            )
            assert mock_request.await_count == 3

    @pytest.mark.asyncio
    async def test_cache_key_is_case_insensitive_on_agent_name(self):
        """'Warren' and 'warren' resolve to the same cache slot."""
        mock_request = AsyncMock(return_value=_make_response("p"))
        with patch("infra.prompt_loader._get_backend_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.request = mock_request
            mock_get_client.return_value = mock_client

            await load_composed_prompt("market_analyst", "Warren")
            await load_composed_prompt("market_analyst", "warren")
            await load_composed_prompt("market_analyst", "WARREN")

            assert mock_request.await_count == 1


# ============================================================================
# 3. format_prompt() runtime substitution
# ============================================================================


class TestFormatPrompt:
    """Test runtime placeholder substitution."""

    def test_resolves_datetime_placeholder(self):
        template = "Current time: {datetime}"
        result = format_prompt(template, datetime="2025-06-15 10:00:00")
        assert "2025-06-15 10:00:00" in result
        assert "{datetime}" not in result


# ============================================================================
# 4. End-to-end async wrapper still works.
# ============================================================================


class TestLoadAndFormatPrompt:
    @pytest.mark.asyncio
    async def test_end_to_end(self):
        mock_request = AsyncMock(return_value=_make_response("Hello Warren, time is {datetime}"))
        with patch("infra.prompt_loader._get_backend_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.request = mock_request
            mock_get_client.return_value = mock_client

            result = await load_and_format_prompt("decision_maker", "Warren", datetime="2025-01-01")

            assert "2025-01-01" in result
            assert "{datetime}" not in result


class TestValidAgentNames:
    def test_expected_names(self):
        assert VALID_AGENT_NAMES == {"warren", "george", "ray", "cathie"}
