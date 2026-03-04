"""Unified Backend Client for all backend API calls.

Consolidates all HTTP communication with the Java backend:
- Trading operations (buy, sell, account report)
- Run tracking (create, update phase, complete)
- Agent management (initialize)

Uses a shared AsyncClient for connection pooling (httpx best practice).

Lifecycle strategy — "loop-local singleton with optional DI":

  Production path (no client injected):
    A single BackendClient is created via get_backend_client() and reused for
    the lifetime of the process.  Internally it lazily creates an
    httpx.AsyncClient and tracks the asyncio event-loop ID so it can detect
    when the loop changes (e.g. between pytest-asyncio test runs that use
    per-function event loops) and transparently recreate the underlying HTTP
    client.  This is the standard pattern used by Prefect, pydantic-ai, and
    other async libraries that hold long-lived HTTP clients.

  Test path (client injected):
    Callers can pass a pre-built httpx.AsyncClient into __init__.  When an
    external client is provided the loop-tracking logic is bypassed entirely
    — the caller owns the client lifecycle.  This makes unit tests trivial:
    inject a client created on the test's own event loop and no stale-socket
    issues can occur.
"""

import logging
from typing import Any, Dict, Optional

import httpx

from config import (
    BACKEND_BASE_URL,
    BACKEND_API_ACCOUNTS,
    BACKEND_API_TRADING_RUNS,
)
from models import TradeResult
from models.api_responses import AccountReport, RecentActivityResponse, SymbolHistoryResponse
from models.run_tracking import CompleteRunData
from exceptions import BackendAPIError

logger = logging.getLogger(__name__)


class BackendClient:
    """Centralized client for all backend API operations.

    Provides typed methods for:
    - Trading: buy_shares, sell_shares, get_account_report
    - Run tracking: create_run, update_phase, complete_run
    - Agent management: initialize_agent

    Supports two modes of operation:

    1. **Production (default)** — no ``client`` argument.  An internal
       ``httpx.AsyncClient`` is lazily created on first use and automatically
       recreated whenever the asyncio event loop changes (loop-local singleton
       pattern).  This keeps TCP connection pooling while avoiding
       ``RuntimeError: Event loop is closed`` across pytest-asyncio test
       boundaries.

    2. **Injected (testing / advanced)** — pass an ``httpx.AsyncClient`` via
       the ``client`` parameter.  The injected client is used as-is; no
       loop-ID tracking is performed.  The caller owns the client lifecycle.
    """

    def __init__(
        self,
        client: Optional[httpx.AsyncClient] = None,
        timeout: float = 30.0,
    ):
        """Initialize the backend client.

        Args:
            client: Optional externally-managed ``httpx.AsyncClient``.  When
                provided, this client is used directly and no internal
                loop-tracking is performed (test / DI path).  When ``None``
                (the default), an internal client is lazily created and
                managed with loop-aware lifecycle (production path).
            timeout: Default request timeout in seconds.  Only used when no
                external *client* is provided.
        """
        self._external_client: Optional[httpx.AsyncClient] = client
        self._owned_client: Optional[httpx.AsyncClient] = None
        self._timeout = timeout
        self._loop_id: Optional[int] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Return the ``httpx.AsyncClient`` to use for the next request.

        **Injected path** — when an external client was passed to ``__init__``,
        it is returned immediately.  No loop-ID tracking is performed because
        the caller owns the client lifecycle.

        **Production path** — a loop-local singleton is lazily created.  The
        asyncio event-loop ``id()`` is recorded on first creation; on every
        subsequent call the current loop ID is compared to the stored one.  If
        the loop changed (common under pytest-asyncio's per-function loop
        scope) the old client is silently discarded and a fresh one is created
        on the new loop.  We intentionally do *not* call ``aclose()`` on the
        stale client because its event loop may already be dead, making the
        async close impossible.

        Why ``is_closed`` alone is not enough: ``httpx.AsyncClient.is_closed``
        only becomes ``True`` after an explicit ``aclose()`` call.  A client
        whose underlying TCP sockets are bound to a dead event loop still
        reports ``is_closed == False``, so the loop-ID comparison is the only
        reliable way to detect staleness.

        References:
            - httpx #2959: AsyncClient pooled connections fail across event loops
              https://github.com/encode/httpx/discussions/2959
            - pytest-asyncio default per-function loop scope:
              https://pytest-asyncio.readthedocs.io/en/stable/how-to-guides/change_default_fixture_loop.html
            - SO #72960518: Singleton async clients confirmed as root cause of
              "Event loop is closed"
              https://stackoverflow.com/questions/72960518
        """
        # --- Injected (DI / test) path ---
        if self._external_client is not None:
            return self._external_client

        # --- Production path: loop-local singleton ---
        # Thread-safety note: This check-then-assign looks like a TOCTOU race,
        # but it is safe. asyncio uses cooperative scheduling — coroutines only
        # yield at `await` points, and this method has none, so it runs atomically.
        import asyncio
        try:
            current_loop_id = id(asyncio.get_running_loop())
        except RuntimeError:
            current_loop_id = None

        if self._owned_client is None or self._owned_client.is_closed or self._loop_id != current_loop_id:
            self._owned_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
            self._loop_id = current_loop_id
        return self._owned_client
    
    async def close(self) -> None:
        """Close the internally-owned client.  Call during application shutdown.

        If an external client was injected, this is a no-op — the caller is
        responsible for closing it.
        """
        if self._owned_client is not None and not self._owned_client.is_closed:
            await self._owned_client.aclose()
            logger.debug("Closed httpx AsyncClient")
        self._owned_client = None
    
    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Make HTTP request to backend API.
        
        Args:
            method: HTTP method (GET, POST, PUT, PATCH, etc.)
            url: Full URL
            params: URL query parameters
            json_data: JSON request body
            
        Returns:
            httpx.Response object
            
        Raises:
            BackendAPIError: On any HTTP error, network error, or timeout
        """
        client = self._get_client()
        
        try:
            logger.debug(f"{method} {url} params={params} json={json_data}")
            
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
            )
            
            logger.debug(f"{method} {url} -> HTTP {response.status_code}")
            response.raise_for_status()
            return response
            
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            try:
                error_body = e.response.json()
                error_msg = error_body.get("error", str(error_body))
            except Exception:
                error_msg = e.response.text
            
            logger.error(f"HTTP {status} {method} {url}: {error_msg}")
            raise BackendAPIError(f"HTTP {status}: {error_msg}", status_code=status) from e
            
        except httpx.TimeoutException as e:
            logger.error(f"Timeout: {method} {url}")
            raise BackendAPIError(f"Request timeout") from e
            
        except httpx.RequestError as e:
            logger.error(f"Network error {method} {url}: {type(e).__name__}: {e}")
            raise BackendAPIError(f"Network error: {str(e)}") from e
    
    # ========== Trading Operations ==========
    
    async def initialize_agent(self, name: str, initial_balance: float = 100000.0) -> int:
        """Initialize agent account if it doesn't exist.

        This is idempotent - safe to call multiple times. If the agent already
        exists (backend returns 400), falls back to looking up the agent by name.

        Args:
            name: Agent name (Warren, George, Ray, Cathie)
            initial_balance: Starting balance in USD

        Returns:
            agent_id from backend

        Raises:
            BackendAPIError: If initialization fails or backend doesn't return agent_id
        """
        url = BACKEND_API_ACCOUNTS
        try:
            response = await self._request("POST", url, json_data={
                "agentName": name,
                "initialBalance": initial_balance
            })
            data = response.json()
            agent_id = data.get("id") if isinstance(data, dict) else None
            if agent_id is None:
                raise BackendAPIError(f"Backend did not return agent_id for {name}")
            logger.info(f"Agent {name} (id={agent_id}) initialized with ${initial_balance:,.2f}")
            return agent_id
        except BackendAPIError as e:
            if e.status_code == 400:
                # Agent likely already exists — look up by name
                logger.info(f"Agent {name} may already exist (HTTP 400), looking up...")
                return await self._lookup_agent_id(name)
            raise

    async def _lookup_agent_id(self, name: str) -> int:
        """Look up an existing agent's ID by name via GET /api/agents.

        Used as a fallback when initialize_agent gets HTTP 400 (agent exists).
        """
        agents_url = f"{BACKEND_BASE_URL}/api/agents"
        response = await self._request("GET", agents_url)
        data = response.json()
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        for agent in data:
            if agent.get("name") == name:
                agent_id = agent["id"]
                logger.info(f"Found existing agent {name} (id={agent_id})")
                return agent_id
        raise BackendAPIError(f"Agent {name} not found in registry after 400 response")
    
    async def get_account_report(self, agent_id: int) -> AccountReport:
        """Get full account report with balance, holdings, and portfolio metrics.

        Uses the enriched AccountReportDto endpoint which returns everything
        in a single call (balance, holdings, portfolio value, P&L, etc.).

        Args:
            agent_id: Backend identifier for the agent

        Returns:
            AccountReport with balance, holdings, portfolio metrics, P&L.
        """
        url = f"{BACKEND_BASE_URL}/api/accounts/resources/accounts/{agent_id}"
        response = await self._request("GET", url)
        return AccountReport.model_validate(response.json())

    async def buy_shares(
        self,
        agent_id: int,
        symbol: str,
        quantity: int,
        run_id: Optional[int] = None,
    ) -> TradeResult:
        """Buy shares of a stock.
        
        Args:
            agent_id: Backend identifier for the agent
            symbol: Stock symbol (e.g., 'AAPL')
            quantity: Number of shares to buy
            run_id: Optional run ID to link this trade
            
        Returns:
            TradeResult with tradeId, symbol, quantity, price, newBalance
        """
        url = f"{BACKEND_API_ACCOUNTS}/{agent_id}/trades"
        response = await self._request("POST", url, json_data={
            "type": "BUY",
            "symbol": symbol,
            "quantity": quantity,
            "runId": run_id
        })
        return TradeResult(**response.json())
    
    async def sell_shares(
        self,
        agent_id: int,
        symbol: str,
        quantity: int,
        run_id: Optional[int] = None,
    ) -> TradeResult:
        """Sell shares of a stock.
        
        Args:
            agent_id: Backend identifier for the agent
            symbol: Stock symbol (e.g., 'AAPL')
            quantity: Number of shares to sell
            run_id: Optional run ID to link this trade
            
        Returns:
            TradeResult with tradeId, symbol, quantity, price, newBalance
        """
        url = f"{BACKEND_API_ACCOUNTS}/{agent_id}/trades"
        response = await self._request("POST", url, json_data={
            "type": "SELL",
            "symbol": symbol,
            "quantity": quantity,
            "runId": run_id
        })
        return TradeResult(**response.json())
    
    # ========== Memory / History Operations ==========

    async def get_trading_history(
        self, agent_id: int, symbol: str, days: int = 30
    ) -> SymbolHistoryResponse:
        """Get complete trading history for a specific stock.

        Args:
            agent_id: Agent ID (integer)
            symbol: Stock symbol (e.g., "NVDA")
            days: How many days back to look (default 30)

        Returns:
            SymbolHistoryResponse with typed trading history

        Raises:
            BackendAPIError: If API call fails
        """
        url = f"{BACKEND_BASE_URL}/api/accounts/{agent_id}/runs/trading-history"
        params = {"symbol": symbol, "days": days}
        response = await self._request("GET", url, params=params)
        return SymbolHistoryResponse.model_validate_json(response.text)

    async def get_recent_activity(
        self, agent_id: int, days: int = 7
    ) -> RecentActivityResponse:
        """Get recent trading activity across all stocks.

        Args:
            agent_id: Agent ID (integer)
            days: How many days back to look (default 7)

        Returns:
            RecentActivityResponse with typed activity data

        Raises:
            BackendAPIError: If API call fails
        """
        url = f"{BACKEND_BASE_URL}/api/accounts/{agent_id}/runs/recent-activity"
        params = {"days": days}
        response = await self._request("GET", url, params=params)
        return RecentActivityResponse.model_validate_json(response.text)

    # ========== Run Tracking Operations ==========
    
    async def create_run(self, agent_id: int) -> int:
        """Create a new trading run.
        
        Args:
            agent_id: Backend identifier for the agent
            
        Returns:
            Run ID for tracking this cycle
            
        Raises:
            BackendAPIError: If run creation fails
        """
        url = BACKEND_API_TRADING_RUNS
        response = await self._request("POST", url, json_data={"agentId": agent_id})
        
        result = response.json()
        run_id = result.get("runId")
        if run_id is None:
            raise BackendAPIError(f"create_run response missing runId: {result}")
        
        logger.info(f"Created trading run #{run_id} for agent {agent_id}")
        return run_id
    
    async def update_phase(self, run_id: int, phase: str) -> None:
        """Update the phase of a trading run.
        
        Args:
            run_id: The run ID to update
            phase: New phase (INITIALIZING, RESEARCHING, DECIDING, TRADING, COMPLETED, ERROR)
        """
        url = f"{BACKEND_API_TRADING_RUNS}/{run_id}/phase"
        await self._request("PATCH", url, json_data={"phase": phase})
        logger.info(f"Updated run #{run_id} to phase {phase}")
    
    async def complete_run(self, run_id: int, data: CompleteRunData) -> None:
        """Complete a trading run with all phase data.
        
        Args:
            run_id: The run ID to complete
            data: CompleteRunData containing all phase information
        """
        url = f"{BACKEND_API_TRADING_RUNS}/{run_id}/complete"
        await self._request("PUT", url, json_data=data.to_json_dict())
        logger.info(f"Completed run #{run_id} with decision={data.decision.decision}")


# Module-level singleton for backward compatibility
_default_client: Optional[BackendClient] = None


def get_backend_client() -> BackendClient:
    """Get the default BackendClient singleton.
    
    For most use cases, use this function to get a shared client instance.
    """
    global _default_client
    if _default_client is None:
        _default_client = BackendClient()
    return _default_client


async def close_backend_client() -> None:
    """Close the default BackendClient. Call during application shutdown."""
    global _default_client
    if _default_client is not None:
        await _default_client.close()
        _default_client = None


# ========== Backward Compatibility Functions ==========
# These wrap the BackendClient methods for existing code that imports from http_client

async def call_backend(
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
) -> httpx.Response:
    """Legacy function for backward compatibility.

    New code should use BackendClient directly.
    """
    client = get_backend_client()
    return await client._request(method, url, params=params, json_data=json_data)
