"""Custom exceptions for the trading agent system."""

from typing import Optional


class BackendAPIError(Exception):
    """Backend API request failed.

    Raised for:
    - HTTP errors (4xx, 5xx status codes)
    - Network errors (connection timeout, DNS failure)
    - Invalid responses (malformed JSON, missing expected fields)
    """

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code

    def __str__(self) -> str:
        base = super().__str__()
        if self.status_code:
            return f"{base} (status={self.status_code})"
        return base
