from unittest.mock import AsyncMock, patch

import pytest

import tools.market_tools as market_tools
from infra.exceptions import BackendAPIError
from models import MarketData
from tools.market_tools import _lookup_share_price, _put_cache


@pytest.mark.asyncio
class TestLookupSharePriceErrorHandling:
    async def test_404_returns_sentinel_value(self):
        with patch("tools.market_tools._fetch_market_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = BackendAPIError("Symbol not found", status_code=404)
            result = await _lookup_share_price("INVALID")
            assert result == -1.0
            mock_fetch.assert_awaited_once_with("INVALID")

    async def test_500_raises_exception(self):
        with patch("tools.market_tools._fetch_market_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = BackendAPIError("Internal server error", status_code=500)
            with pytest.raises(BackendAPIError) as exc_info:
                await _lookup_share_price("AAPL")
            assert exc_info.value.status_code == 500
            mock_fetch.assert_awaited_once_with("AAPL")

    async def test_successful_lookup_returns_price(self):
        with patch("tools.market_tools._fetch_market_data", new_callable=AsyncMock) as mock_fetch:
            mock_data = MarketData(
                symbol="AAPL",
                price=195.50,
                cached=False,
                timestamp="2026-04-20T12:00:00Z",
                source="Finnhub",
            )
            mock_fetch.return_value = mock_data
            result = await _lookup_share_price("AAPL")
            assert result == 195.50
            mock_fetch.assert_awaited_once_with("AAPL")


class TestMarketDataCacheBounded:
    def _make_market_data(self, symbol: str) -> MarketData:
        return MarketData(
            symbol=symbol,
            price=100.0,
            cached=False,
            timestamp="2026-04-20T12:00:00Z",
            source="Finnhub",
        )

    def test_cache_evicts_oldest_when_exceeding_maxsize(self):
        market_tools._market_data_cache.clear()

        for i in range(500):
            _put_cache(f"SYM{i:04d}", self._make_market_data(f"SYM{i:04d}"))

        assert len(market_tools._market_data_cache) == 500
        assert "SYM0000" in market_tools._market_data_cache

        _put_cache("SYM0500", self._make_market_data("SYM0500"))

        assert (
            len(market_tools._market_data_cache) == 500
        ), "Cache size must stay bounded at maxsize=500 after eviction"
        assert (
            "SYM0000" not in market_tools._market_data_cache
        ), "Oldest entry should have been evicted when cache exceeded maxsize=500"
        assert "SYM0500" in market_tools._market_data_cache
