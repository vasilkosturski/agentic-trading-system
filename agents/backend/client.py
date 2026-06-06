"""Unified Backend Client.

Loop-local: rebinds httpx.AsyncClient when the asyncio loop changes
(pytest-asyncio per-function loops); tests may inject an externally-owned client.
"""

import asyncio
import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from backend.auth import JwtAuth
from config import (
    BACKEND_API_ACCOUNTS,
    BACKEND_API_TRADING_RUNS,
    BACKEND_BASE_URL,
    config,
)
from infra.exceptions import BackendAPIError
from models import TradeResult
from models.api_responses import AccountReport, RecentActivityResponse, SymbolHistoryResponse
from models.run_tracking import CompleteRunData

logger = logging.getLogger(__name__)


# Trade endpoints (buy_shares / sell_shares) are intentionally NOT decorated
# until the backend supports idempotency keys — otherwise a transient timeout
# that already reached the server could result in duplicate trade execution.
_retry_on_transient = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=16),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)),
    reraise=True,
)


def _default_credentials_provider() -> tuple[str, str]:
    """Read admin credentials from ``config`` at login time."""
    return config.BACKEND_ADMIN_USERNAME, config.BACKEND_ADMIN_PASSWORD


class BackendClient:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
        credentials_provider=_default_credentials_provider,
    ):
        self._external_client: httpx.AsyncClient | None = client
        self._owned_client: httpx.AsyncClient | None = None
        self._timeout = timeout
        self._loop_id: int | None = None
        # One JwtAuth per BackendClient — the token cache lives in the auth
        # object, so a fresh BackendClient implies a fresh login. Lazily
        # constructed so tests can swap ``credentials_provider`` between
        # construction and first use.
        self._credentials_provider = credentials_provider
        self._auth: JwtAuth | None = None

    def _get_auth(self) -> JwtAuth:
        if self._auth is None:
            self._auth = JwtAuth(
                login_url=f"{BACKEND_BASE_URL}/api/auth/login",
                credentials_provider=self._credentials_provider,
            )
        return self._auth

    def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client

        # Thread-safety: this check-then-assign looks like a TOCTOU race, but
        # asyncio uses cooperative scheduling — coroutines only yield at
        # `await` points and this method has none, so it runs atomically.
        try:
            current_loop_id = id(asyncio.get_running_loop())
        except RuntimeError:
            current_loop_id = None

        # ``is_closed`` only flips to True after an explicit aclose(); a client
        # whose sockets are bound to a dead event loop still reports
        # ``is_closed == False``, so loop-ID comparison is the only reliable
        # staleness signal (avoids "Event loop is closed" at request time).
        if (
            self._owned_client is None
            or self._owned_client.is_closed
            or self._loop_id != current_loop_id
        ):
            # HTTP/2 negotiated via ALPN; granular timeouts fail fast on
            # connect/pool and allow longer reads for heavier endpoints.
            self._owned_client = httpx.AsyncClient(
                http2=True,
                timeout=httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                headers={"Accept": "application/json"},
            )
            self._loop_id = current_loop_id
        return self._owned_client

    async def close(self) -> None:
        # No-op when an external client was injected; that caller owns its
        # lifecycle.
        if self._owned_client is not None and not self._owned_client.is_closed:
            await self._owned_client.aclose()
            logger.debug("Closed httpx AsyncClient")
        self._owned_client = None

    async def _dispatch_with_auth(
        self,
        client: httpx.AsyncClient,
        *,
        method: str,
        url: str,
        params: dict[str, Any] | None,
        json_data: dict[str, Any] | None,
    ) -> httpx.Response:
        """Drive ``JwtAuth.auth_flow`` against ``client``.

        The auth flow is a generator that yields ``httpx.Request`` objects and
        is sent back the corresponding ``httpx.Response`` — exactly the
        protocol ``httpx.Auth`` defines. Driving it explicitly here means the
        auth pipeline works against both the production owned client and the
        ``_FakeHttpxClient`` test doubles that don't go through httpx's own
        auth machinery. JSON payloads are tracked alongside the seed request
        so each dispatch passes the original ``params`` / ``json_data`` while
        the auth flow only contributes the ``Authorization`` header and the
        login POST.
        """
        auth = self._get_auth()
        seed = httpx.Request(method=method, url=url)
        flow = auth.auth_flow(seed)
        request = next(flow)
        login_url = f"{BACKEND_BASE_URL}/api/auth/login"
        while True:
            is_login = str(request.url) == login_url
            if is_login:
                # The login request body lives on the httpx.Request object the
                # auth flow built — extract it and forward as JSON to the
                # underlying client. The flow always sets ``Content-Type:
                # application/json`` on login.
                body = _json_body_from_request(request)
                response = await client.request(
                    method=request.method,
                    url=str(request.url),
                    params=None,
                    json=body,
                    headers=None,
                )
            else:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers={"Authorization": request.headers["Authorization"]},
                )
            try:
                request = flow.send(response)
            except StopIteration:
                return response

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        client = self._get_client()

        try:
            logger.debug(f"{method} {url} params={params} json={json_data}")

            response = await self._dispatch_with_auth(
                client,
                method=method,
                url=url,
                params=params,
                json_data=json_data,
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
            raise BackendAPIError("Request timeout") from e

        except httpx.RequestError as e:
            logger.error(f"Network error {method} {url}: {type(e).__name__}: {e}")
            raise BackendAPIError(f"Network error: {str(e)}") from e

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        return await self._request(method, url, params=params, json_data=json_data)

    async def initialize_agent(self, name: str, initial_balance: float = 100000.0) -> int:
        # Idempotent: when the agent already exists the backend returns HTTP
        # 400 with an "already exists" message — fall back to lookup. Any
        # other 400 (validation, forbidden chars, etc.) propagates as-is so
        # the real cause isn't hidden behind a misleading "not found in
        # registry" error.
        url = BACKEND_API_ACCOUNTS
        try:
            response = await self._request(
                "POST", url, json_data={"name": name, "initialBalance": initial_balance}
            )
            data = response.json()
            agent_id = data.get("id") if isinstance(data, dict) else None
            if agent_id is None:
                raise BackendAPIError(f"Backend did not return agent_id for {name}")
            logger.info(f"Agent {name} (id={agent_id}) initialized with ${initial_balance:,.2f}")
            return agent_id
        except BackendAPIError as e:
            if e.status_code == 400 and "already exists" in str(e).lower():
                logger.info(f"Agent {name} already exists (HTTP 400), looking up...")
                return await self._lookup_agent_id(name)
            raise

    async def _lookup_agent_id(self, name: str) -> int:
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

    @_retry_on_transient
    async def get_account_report(self, agent_id: int) -> AccountReport:
        url = f"{BACKEND_BASE_URL}/api/accounts/resources/accounts/{agent_id}"
        response = await self._request("GET", url)
        return AccountReport.model_validate_json(response.text)

    async def buy_shares(
        self,
        agent_id: int,
        symbol: str,
        quantity: int,
        run_id: int | None = None,
    ) -> TradeResult:
        url = f"{BACKEND_API_ACCOUNTS}/{agent_id}/trades"
        response = await self._request(
            "POST",
            url,
            json_data={"type": "BUY", "symbol": symbol, "quantity": quantity, "runId": run_id},
        )
        return TradeResult.model_validate_json(response.text)

    async def sell_shares(
        self,
        agent_id: int,
        symbol: str,
        quantity: int,
        run_id: int | None = None,
    ) -> TradeResult:
        url = f"{BACKEND_API_ACCOUNTS}/{agent_id}/trades"
        response = await self._request(
            "POST",
            url,
            json_data={"type": "SELL", "symbol": symbol, "quantity": quantity, "runId": run_id},
        )
        return TradeResult.model_validate_json(response.text)

    async def get_trading_history(
        self, agent_id: int, symbol: str, days: int = 30
    ) -> SymbolHistoryResponse:
        url = f"{BACKEND_BASE_URL}/api/accounts/{agent_id}/runs/trading-history"
        params = {"symbol": symbol, "days": days}
        response = await self._request("GET", url, params=params)
        return SymbolHistoryResponse.model_validate_json(response.text)

    @_retry_on_transient
    async def get_recent_activity(self, agent_id: int, days: int = 7) -> RecentActivityResponse:
        url = f"{BACKEND_BASE_URL}/api/accounts/{agent_id}/runs/recent-activity"
        params = {"days": days}
        response = await self._request("GET", url, params=params)
        return RecentActivityResponse.model_validate_json(response.text)

    @_retry_on_transient
    async def create_run(self, agent_id: int) -> int:
        url = BACKEND_API_TRADING_RUNS
        response = await self._request("POST", url, json_data={"agentId": agent_id})

        result = response.json()
        run_id = result.get("runId")
        if run_id is None:
            raise BackendAPIError(f"create_run response missing runId: {result}")

        logger.info(f"Created trading run #{run_id} for agent {agent_id}")
        return run_id

    @_retry_on_transient
    async def update_phase(self, run_id: int, phase: str, error_message: str | None = None) -> None:
        url = f"{BACKEND_API_TRADING_RUNS}/{run_id}/phase"
        payload: dict = {"phase": phase}
        if error_message is not None:
            payload["errorMessage"] = error_message
        await self._request("PATCH", url, json_data=payload)
        logger.info(f"Updated run #{run_id} to phase {phase}")

    @_retry_on_transient
    async def complete_run(self, run_id: int, data: CompleteRunData) -> None:
        url = f"{BACKEND_API_TRADING_RUNS}/{run_id}/complete"
        await self._request("PUT", url, json_data=data.to_json_dict())
        logger.info(f"Completed run #{run_id} with decision={data.decision.decision}")


# Process-wide BackendClient slot — the running-loop check in
# ``get_backend_client`` makes the check-then-assign race-free under
# cooperative scheduling and crashes loudly if a sync thread reaches it.
_default_client: BackendClient | None = None


def get_backend_client() -> BackendClient:
    # The running-loop check is load-bearing: a sync thread calling this would
    # build a BackendClient bound to no event loop, which then fails at request
    # time with a confusing "Event loop is closed" error. Crash early with a
    # domain exception instead.
    try:
        asyncio.get_running_loop()
    except RuntimeError as e:
        raise BackendAPIError("get_backend_client called outside an event loop") from e

    global _default_client
    if _default_client is None:
        _default_client = BackendClient()
    return _default_client


async def close_backend_client() -> None:
    global _default_client
    if _default_client is not None:
        await _default_client.close()
        _default_client = None


def _json_body_from_request(request: httpx.Request) -> dict | None:
    """Decode the JSON body httpx serialized into a Request."""
    import json

    body = request.read()
    if not body:
        return None
    return json.loads(body)
