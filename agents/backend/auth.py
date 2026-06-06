"""JWT auth scheme for the backend.

`JwtAuth` is an ``httpx.Auth`` subclass that handles the agents-pod login flow
and bearer-token injection for every request. The class hides three concerns
behind a single object that plugs into ``httpx.AsyncClient(auth=...)``:

* POST `/api/auth/login` with admin credentials, parse the returned JWT.
* Cache the JWT and attach ``Authorization: Bearer <token>`` to outgoing
  requests.
* On HTTP 401, invalidate the cached token, re-login once, and retry the
  original request. A second 401 is yielded back to the caller for upstream
  error mapping (callers translate it to ``BackendAPIError(status=401)``).

Credentials are obtained from a ``credentials_provider`` callable so tests can
inject deterministic values without monkeypatching module globals.
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Any

import httpx

from infra.exceptions import BackendAPIError


class JwtAuth(httpx.Auth):
    """``httpx.Auth`` implementation for the backend's JWT login flow."""

    # httpx.Auth contract: signal that the auth flow may need to read the
    # response body (the login POST) before yielding the next request.
    requires_response_body = True

    def __init__(
        self,
        *,
        login_url: str,
        credentials_provider: Callable[[], tuple[str, str]],
    ) -> None:
        self._login_url = login_url
        self._credentials_provider = credentials_provider
        self._token: str | None = None

    def sync_auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        raise RuntimeError("JwtAuth only supports async clients; use httpx.AsyncClient.")

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        """Auth flow used by both async and sync clients via httpx's protocol.

        httpx routes both ``sync_auth_flow`` and ``async_auth_flow`` through
        ``auth_flow`` when neither is overridden — overriding ``auth_flow``
        gives us one implementation that works for the async client we use in
        production and the sync clients tests sometimes spin up directly.
        """
        if self._token is None:
            self._token = yield from self._login_and_parse_token()

        request.headers["Authorization"] = f"Bearer {self._token}"
        response = yield request

        if response.status_code == 401:
            # Token may have expired mid-flight — drop the cached value,
            # re-login once, and retry. A second 401 is yielded back so the
            # caller's error mapping surfaces it as a hard failure.
            self._token = None
            self._token = yield from self._login_and_parse_token()
            request.headers["Authorization"] = f"Bearer {self._token}"
            yield request

    def _login_and_parse_token(
        self,
    ) -> Generator[httpx.Request, httpx.Response, str]:
        username, password = self._credentials_provider()
        login_request = httpx.Request(
            "POST",
            self._login_url,
            json={"username": username, "password": password},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        response = yield login_request
        if response.status_code != 200:
            raise BackendAPIError(
                f"Login failed: HTTP {response.status_code}",
                status_code=response.status_code,
            )
        body: dict[str, Any] = response.json()
        token = body.get("token")
        if not token:
            raise BackendAPIError("Login response missing 'token' field")
        return token
