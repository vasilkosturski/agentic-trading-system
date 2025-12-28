"""Unified HTTP client for backend API calls.

All backend communication goes through this module for:
- Consistent error handling
- Centralized logging
- Configurable timeouts
- Easy testing (mock one function instead of httpx everywhere)
"""

import logging
import httpx
from typing import Optional, Dict, Any

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


async def call_backend(
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
) -> httpx.Response:
    """Make HTTP request to backend API.

    This is the ONLY HTTP client function. All tools use this.

    Args:
        method: HTTP method (GET, POST, PUT, etc.)
        url: Full URL (e.g., f"{BACKEND_URL}/{agent_id}/balance")
        params: URL query parameters (for GET requests)
        json_data: JSON request body (for POST requests)
        timeout: Request timeout in seconds (default: 30)

    Returns:
        httpx.Response object with status_code, text(), json() methods
        Caller decides how to parse response based on use case

    Raises:
        BackendAPIError: On any HTTP error, network error, or timeout
            - Includes status_code attribute for HTTP errors
            - Logs full context before raising

    Example:
        # Trading tool (wants to raise on error)
        response = await call_backend("POST", url, json_data=payload)
        return response.json()["data"]

        # Memory tool (wants to return JSON string)
        try:
            response = await call_backend("GET", url, params=params)
            return response.text
        except BackendAPIError as e:
            if e.status_code == 404:
                return '{"error": "Not found"}'
            return f'{{"error": "{str(e)}"}}'
    """
    try:
        logger.debug(f"{method} {url} params={params} json={json_data}")

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
            )

            logger.debug(f"{method} {url} -> HTTP {response.status_code}")

            # Raise for 4xx and 5xx status codes
            response.raise_for_status()

            return response

    except httpx.HTTPStatusError as e:
        # HTTP errors (4xx, 5xx)
        status = e.response.status_code
        try:
            error_body = e.response.json()
            error_msg = error_body.get("error", str(error_body))
        except Exception:
            error_msg = e.response.text

        logger.error(f"HTTP {status} {method} {url}: {error_msg}")
        raise BackendAPIError(f"HTTP {status}: {error_msg}", status_code=status) from e

    except httpx.TimeoutException as e:
        logger.error(f"Timeout after {timeout}s: {method} {url}")
        raise BackendAPIError(f"Request timeout after {timeout}s") from e

    except httpx.RequestError as e:
        # Network errors (DNS, connection refused, etc.)
        logger.error(f"Network error {method} {url}: {type(e).__name__}: {e}")
        raise BackendAPIError(f"Network error: {str(e)}") from e

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error {method} {url}: {type(e).__name__}: {e}")
        raise BackendAPIError(f"Unexpected error: {str(e)}") from e
