"""Tests for market_tools.py error handling.

Tests the graceful error handling pattern for failed symbol lookups:
- 404 errors return -1.0 sentinel value (symbol not found)
- Fatal errors (5xx, timeout) still raise exceptions
- Agents can continue with other candidates when some symbols fail
"""

import pytest
from unittest.mock import AsyncMock, patch

from market_tools import _lookup_share_price
from exceptions import BackendAPIError


@pytest.mark.asyncio
class TestLookupSharePriceErrorHandling:
    """Test graceful error handling for failed symbol lookups."""

    async def test_404_returns_sentinel_value(self):
        """404 errors (symbol not found) should return -1.0 sentinel, not raise."""
        with patch('market_tools._fetch_market_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = BackendAPIError("Symbol not found", status_code=404)
            result = await _lookup_share_price("INVALID")
            assert result == -1.0
            mock_fetch.assert_awaited_once_with("INVALID")

    async def test_500_raises_exception(self):
        """5xx errors (backend issues) should raise BackendAPIError."""
        with patch('market_tools._fetch_market_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = BackendAPIError("Internal server error", status_code=500)
            with pytest.raises(BackendAPIError) as exc_info:
                await _lookup_share_price("AAPL")
            assert exc_info.value.status_code == 500
            mock_fetch.assert_awaited_once_with("AAPL")

    async def test_successful_lookup_returns_price(self):
        """Successful lookups should return the actual price."""
        from models import MarketData

        with patch('market_tools._fetch_market_data', new_callable=AsyncMock) as mock_fetch:
            mock_data = MarketData(
                symbol="AAPL",
                price=195.50,
                cached=False,
                timestamp="2026-04-20T12:00:00Z",
                source="Finnhub"
            )
            mock_fetch.return_value = mock_data
            result = await _lookup_share_price("AAPL")
            assert result == 195.50
            mock_fetch.assert_awaited_once_with("AAPL")
