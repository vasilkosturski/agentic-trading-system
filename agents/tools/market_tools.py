import logging

from agents import function_tool
from cachetools import TTLCache

from backend.client import BackendAPIError, get_backend_client
from config import BACKEND_API_MARKET
from models import MarketData, PriceMetadata

logger = logging.getLogger(__name__)

BACKEND_URL = BACKEND_API_MARKET

_CACHE_TTL_SECONDS = 300

_market_data_cache: TTLCache = TTLCache(maxsize=500, ttl=_CACHE_TTL_SECONDS)


def _get_cached(symbol: str) -> MarketData | None:
    return _market_data_cache.get(symbol.upper())


def _put_cache(symbol: str, data: MarketData) -> None:
    _market_data_cache[symbol.upper()] = data


async def _fetch_market_data(symbol: str, days: int = 30) -> MarketData:
    cached = _get_cached(symbol)
    if cached is not None:
        logger.debug("Cache hit for %s", symbol.upper())
        return cached

    url = f"{BACKEND_URL}/{symbol}?days={days}"
    client = get_backend_client()
    response = await client.request("GET", url)
    data = MarketData(**response.json())
    _put_cache(symbol, data)
    return data


async def _lookup_share_price(symbol: str) -> float:
    try:
        data = await _fetch_market_data(symbol)
        return float(data.price)
    except BackendAPIError as e:
        if e.status_code == 404:
            logger.warning("Symbol %s not found in market data (404) - returning sentinel", symbol)
            return -1.0
        logger.error("Backend error for %s: %s", symbol, e)
        raise
    except Exception as e:
        logger.error("Unexpected error fetching %s: %s", symbol, e)
        raise


@function_tool
async def lookup_share_price(symbol: str) -> float:
    return await _lookup_share_price(symbol)


@function_tool
async def get_price_with_metadata(symbol: str) -> PriceMetadata:
    data = await _fetch_market_data(symbol)
    return PriceMetadata(
        price=data.price,
        cached=data.cached,
        timestamp=data.timestamp,
        source=data.source,
    )


MARKET_TOOLS = [
    lookup_share_price,
    get_price_with_metadata,
]
