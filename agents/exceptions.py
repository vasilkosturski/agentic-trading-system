"""Custom exceptions for the trading agent system."""

from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from utils.sdk_parser import ParsedToolCall


class ToolExecutionError(Exception):
    """Raised when tools fail during agent execution.

    Used to detect and fail fast when tool calls return error responses,
    rather than letting the agent continue with potentially invalid data.
    """

    def __init__(self, message: str, tool_errors: List["ParsedToolCall"]):
        super().__init__(message)
        self.tool_errors = tool_errors

    def __str__(self) -> str:
        base = super().__str__()
        error_names = [e.name for e in self.tool_errors]
        return f"{base} - Failed tools: {error_names}"


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
