"""Unified Backend Client for all backend API calls.

Consolidates all HTTP communication with the Java backend:
- Trading operations (buy, sell, balance, holdings)
- Run tracking (create, update phase, complete)
- Agent management (initialize)

Uses a shared AsyncClient for connection pooling (httpx best practice).
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from config import (
    BACKEND_BASE_URL,
    BACKEND_API_ACCOUNTS,
    BACKEND_API_TRADING_RUNS,
)
from models import Holding, TradeResult
from models.run_tracking import CompleteRunData

logger = logging.getLogger(__name__)


class BackendAPIError(Exception):
    """Backend API request failed.

    Raised for:
    - HTTP errors (4xx, 5xx status codes)
    - Network errors (connection timeout, DNS failure)
    - Invalid responses (malformed JSON, etc.)
    """
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class BackendClient:
    """Centralized client for all backend API operations.
    
    Provides typed methods for:
    - Trading: buy_shares, sell_shares, get_balance, get_holdings
    - Run tracking: create_run, update_phase, complete_run
    - Agent management: initialize_agent
    
    Uses connection pooling for better performance.
    """
    
    def __init__(self, timeout: float = 30.0):
        """Initialize the backend client.
        
        Args:
            timeout: Default request timeout in seconds
        """
        self._client: Optional[httpx.AsyncClient] = None
        self._timeout = timeout
    
    def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared AsyncClient.
        
        Lazy initialization ensures client is created only when needed.
        Reuses TCP connections across requests for better performance.
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
            logger.debug("Created new httpx AsyncClient for backend")
        return self._client
    
    async def close(self) -> None:
        """Close the client. Call during application shutdown."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            logger.debug("Closed httpx AsyncClient")
        self._client = None
    
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
    
    async def initialize_agent(self, name: str, initial_balance: float = 100000.0) -> str:
        """Initialize agent account if it doesn't exist.
        
        This is idempotent - safe to call multiple times.
        
        Args:
            name: Agent name (Warren, George, Ray, Cathie)
            initial_balance: Starting balance in USD
            
        Returns:
            Confirmation message
        """
        url = BACKEND_API_ACCOUNTS
        response = await self._request("POST", url, json_data={
            "agentName": name,
            "initialBalance": initial_balance
        })
        logger.info(f"Agent {name} initialized with ${initial_balance:,.2f}")
        return f"Agent {name} initialized successfully with ${initial_balance:,.2f}"
    
    async def get_balance(self, agent_id: int) -> float:
        """Get the cash balance of an agent.
        
        Args:
            agent_id: Backend identifier for the agent
            
        Returns:
            Current cash balance in USD
        """
        url = f"{BACKEND_API_ACCOUNTS}/{agent_id}/balance"
        response = await self._request("GET", url)
        return float(response.json())
    
    async def get_holdings(self, agent_id: int) -> List[Holding]:
        """Get the stock holdings of an agent.
        
        Args:
            agent_id: Backend identifier for the agent
            
        Returns:
            List of Holding objects with symbol, quantity, averagePrice
        """
        url = f"{BACKEND_API_ACCOUNTS}/{agent_id}/holdings"
        response = await self._request("GET", url)
        return [Holding(**item) for item in response.json()]
    
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
        logger.info(f"Completed run #{run_id} with decision={data.decision.value}")


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
    timeout: int = 30,
) -> httpx.Response:
    """Legacy function for backward compatibility.
    
    New code should use BackendClient directly.
    """
    client = get_backend_client()
    return await client._request(method, url, params=params, json_data=json_data)
