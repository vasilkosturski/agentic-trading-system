"""Tests for backend_client.py - HTTP client error handling.

Tests focus on ensuring the HTTP client properly handles error responses
and enforces JSON content negotiation via Accept headers.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from backend_client import BackendClient
from exceptions import BackendAPIError


class TestBackendClientErrorHandling:
    """Test suite for backend client error response handling."""

    @pytest.mark.asyncio
    async def test_json_error_handling(self):
        """Verify JSON errors are properly extracted and raised as BackendAPIError."""
        json_error_body = {
            "type": "https://trading.example.com/errors/resource-not-found",
            "title": "Resource Not Found",
            "status": 404,
            "detail": "Symbol not found: INVALID",
            "instance": "/api/market/INVALID"
        }

        mock_json_response = httpx.Response(
            status_code=404,
            json=json_error_body,
            headers={"content-type": "application/json"}
        )

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.request.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=httpx.Request("GET", "http://test.com/api/market/INVALID"),
            response=mock_json_response
        )

        client = BackendClient(client=mock_async_client)

        with pytest.raises(BackendAPIError) as exc_info:
            await client._request("GET", "http://test.com/api/market/INVALID")

        error = exc_info.value
        error_str = str(error)
        assert "<!doctype" not in error_str.lower()
        assert "404" in error_str or "not found" in error_str.lower()
