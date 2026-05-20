"""Tests for market_tools.py error handling.

Tests the graceful error handling pattern for failed symbol lookups:
- 404 errors return -1.0 sentinel value (symbol not found)
- Fatal errors (5xx, timeout) still raise exceptions
- Agents can continue with other candidates when some symbols fail
"""

import pytest
from unittest.mock import AsyncMock, patch

import tools.market_tools as market_tools
from tools.market_tools import _lookup_share_price, _put_cache, _get_cached
from infra.exceptions import BackendAPIError
from models import MarketData


@pytest.mark.asyncio
class TestLookupSharePriceErrorHandling:
    """Test graceful error handling for failed symbol lookups."""

    async def test_404_returns_sentinel_value(self):
        """404 errors (symbol not found) should return -1.0 sentinel, not raise."""
        with patch('tools.market_tools._fetch_market_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = BackendAPIError("Symbol not found", status_code=404)
            result = await _lookup_share_price("INVALID")
            assert result == -1.0
            mock_fetch.assert_awaited_once_with("INVALID")

    async def test_500_raises_exception(self):
        """5xx errors (backend issues) should raise BackendAPIError."""
        with patch('tools.market_tools._fetch_market_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = BackendAPIError("Internal server error", status_code=500)
            with pytest.raises(BackendAPIError) as exc_info:
                await _lookup_share_price("AAPL")
            assert exc_info.value.status_code == 500
            mock_fetch.assert_awaited_once_with("AAPL")

    async def test_successful_lookup_returns_price(self):
        """Successful lookups should return the actual price."""
        with patch('tools.market_tools._fetch_market_data', new_callable=AsyncMock) as mock_fetch:
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


class TestMarketDataCacheBounded:
    """W6: The module-level cache must be bounded (cachetools.TTLCache).

    The previous implementation used an unbounded dict, which leaked memory
    when many distinct symbols were requested. The cache is now a
    cachetools.TTLCache with maxsize=500 so it evicts oldest entries when full.
    """

    def _make_market_data(self, symbol: str) -> MarketData:
        return MarketData(
            symbol=symbol,
            price=100.0,
            cached=False,
            timestamp="2026-04-20T12:00:00Z",
            source="Finnhub",
        )

    def test_cache_is_cachetools_ttlcache(self):
        """_market_data_cache must be a cachetools.TTLCache instance."""
        from cachetools import TTLCache
        assert isinstance(market_tools._market_data_cache, TTLCache)

    def test_cache_maxsize_is_500(self):
        """Cache must be bounded at 500 entries."""
        assert market_tools._market_data_cache.maxsize == 500

    def test_cache_ttl_matches_constant(self):
        """Cache TTL must come from the existing module-level constant."""
        assert market_tools._market_data_cache.ttl == market_tools._CACHE_TTL_SECONDS

    def test_cache_evicts_oldest_when_exceeding_maxsize(self):
        """Inserting >500 distinct symbols must evict the oldest entry.

        TTLCache evicts in LRU order when full. Without touching any entries
        between inserts, the first one inserted (SYM0000) is the least-recently
        used and must be evicted when the 501st entry arrives.
        """
        # Reset the cache so this test is independent of prior state.
        market_tools._market_data_cache.clear()

        # Insert 500 entries to fill the cache (no reads in between).
        for i in range(500):
            _put_cache(f"SYM{i:04d}", self._make_market_data(f"SYM{i:04d}"))

        assert len(market_tools._market_data_cache) == 500
        # Direct membership check — avoid `_get_cached` because TTLCache treats
        # `.get()` as a use, which would mark SYM0000 as recently used.
        assert "SYM0000" in market_tools._market_data_cache

        # Insert the 501st entry — the oldest (SYM0000) should be evicted.
        _put_cache("SYM0500", self._make_market_data("SYM0500"))

        assert len(market_tools._market_data_cache) == 500, (
            "Cache size must stay bounded at maxsize=500 after eviction"
        )
        assert "SYM0000" not in market_tools._market_data_cache, (
            "Oldest entry should have been evicted when cache exceeded maxsize=500"
        )
        # The newest entry must be present.
        assert "SYM0500" in market_tools._market_data_cache
