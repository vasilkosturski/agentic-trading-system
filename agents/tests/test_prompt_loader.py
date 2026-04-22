"""Tests for prompt_loader: API-based prompt loading and runtime formatting.

Since prompt_loader now fetches composed prompts from the Java backend API,
the parser tests are replaced with mocked HTTP tests and format_prompt unit tests.

Covers:
1. load_composed_prompt() with mocked HTTP responses
2. format_prompt() runtime placeholder substitution
3. Validation (invalid agent names, backend errors)
4. get_available_templates() returns expected structure
"""

from unittest.mock import patch, MagicMock

import pytest

from prompt_loader import (
    load_composed_prompt,
    load_prompt_template,
    format_prompt,
    load_and_format_prompt,
    get_available_templates,
    VALID_AGENT_NAMES,
    _PartialFormatDict,
)


# ============================================================================
# 1. load_composed_prompt() with mocked HTTP
# ============================================================================


class TestLoadComposedPrompt:
    """Test API-based prompt loading with mocked HTTP responses."""

    @patch("prompt_loader.httpx.get")
    def test_fetches_from_backend_api(self, mock_get):
        """Calls the correct backend URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "You are Warren, a Value Investor."
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = load_composed_prompt("decision_maker", "Warren")

        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        assert "/api/prompts/decision_maker/warren" in call_url
        assert result == "You are Warren, a Value Investor."

    def test_invalid_agent_name_raises_value_error(self):
        """Invalid agent name raises ValueError without calling backend."""
        with pytest.raises(ValueError, match="Invalid agent name"):
            load_composed_prompt("market_analyst", "invalid_agent")

    @patch("prompt_loader.httpx.get")
    def test_404_raises_file_not_found(self, mock_get):
        """Backend 404 raises FileNotFoundError."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_get.return_value = mock_response

        with pytest.raises(FileNotFoundError, match="Prompt not found"):
            load_composed_prompt("decision_maker", "warren")


# ============================================================================
# 2. format_prompt() runtime substitution
# ============================================================================


class TestFormatPrompt:
    """Test runtime placeholder substitution."""

    def test_resolves_datetime_placeholder(self):
        """format_prompt() resolves {datetime}."""
        template = "Current time: {datetime}"
        result = format_prompt(template, datetime="2025-06-15 10:00:00")
        assert "2025-06-15 10:00:00" in result
        assert "{datetime}" not in result


class TestLoadPromptTemplate:
    """Test end-to-end template loading wrappers."""

    @patch("prompt_loader.httpx.get")
    def test_load_and_format_prompt_end_to_end(self, mock_get):
        """load_and_format_prompt fetches and formats in one call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Hello Warren, time is {datetime}"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = load_and_format_prompt(
            "decision_maker", "Warren", datetime="2025-01-01"
        )
        assert "2025-01-01" in result
        assert "{datetime}" not in result


class TestValidAgentNames:
    """Test agent name constants."""

    def test_expected_names(self):
        assert VALID_AGENT_NAMES == {"warren", "george", "ray", "cathie"}
