"""Unified HTTP client for backend API calls.

DEPRECATED: This module is kept for backward compatibility.
New code should import from backend.client directly.

All backend communication now goes through BackendClient class.
"""

# Re-export from backend.client for backward compatibility
from backend.client import (
    BackendAPIError,
    BackendClient,
    get_backend_client,
    close_backend_client,
    call_backend,
)

__all__ = [
    "BackendAPIError",
    "BackendClient", 
    "get_backend_client",
    "close_backend_client",
    "call_backend",
]
