from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from infra.prompt_loader import (
    clear_prompt_cache,
    format_prompt,
    load_and_format_prompt,
    load_composed_prompt,
)


@pytest.fixture(autouse=True)
def _reset_prompt_cache():
    clear_prompt_cache()
    yield
    clear_prompt_cache()


def _make_response(text: str, status_code: int = 200) -> MagicMock:
    mock = MagicMock(spec=httpx.Response)
    mock.text = text
    mock.status_code = status_code
    return mock


class TestLoadComposedPrompt:
    @pytest.mark.asyncio
    async def test_routes_through_backend_client_request(self):
        mock_request = AsyncMock(return_value=_make_response("You are Warren."))
        with patch("infra.prompt_loader._get_backend_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.request = mock_request
            mock_get_client.return_value = mock_client

            result = await load_composed_prompt("decision_maker", "Warren")

            assert result == "You are Warren."
            mock_request.assert_awaited_once()
            args, kwargs = mock_request.call_args
            method = args[0] if args else kwargs.get("method")
            url = args[1] if len(args) > 1 else kwargs.get("url")
            assert method == "GET"
            assert "/api/prompts/decision_maker/warren" in url

    @pytest.mark.asyncio
    async def test_invalid_agent_name_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid agent name"):
            await load_composed_prompt("market_analyst", "invalid_agent")


class TestPromptCache:
    @pytest.mark.asyncio
    async def test_second_call_does_not_trigger_second_http_call(self):
        mock_request = AsyncMock(return_value=_make_response("cached prompt"))
        with patch("infra.prompt_loader._get_backend_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.request = mock_request
            mock_get_client.return_value = mock_client

            first = await load_composed_prompt("market_analyst", "Warren")
            second = await load_composed_prompt("market_analyst", "Warren")

            assert first == "cached prompt"
            assert second == "cached prompt"
            assert mock_request.await_count == 1

    @pytest.mark.asyncio
    async def test_different_keys_each_fetch_once(self):
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
        mock_request = AsyncMock(return_value=_make_response("p"))
        with patch("infra.prompt_loader._get_backend_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.request = mock_request
            mock_get_client.return_value = mock_client

            await load_composed_prompt("market_analyst", "Warren")
            await load_composed_prompt("market_analyst", "warren")
            await load_composed_prompt("market_analyst", "WARREN")

            assert mock_request.await_count == 1


class TestFormatPrompt:
    def test_resolves_datetime_placeholder(self):
        template = "Current time: {datetime}"
        result = format_prompt(template, datetime="2025-06-15 10:00:00")
        assert "2025-06-15 10:00:00" in result
        assert "{datetime}" not in result


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
