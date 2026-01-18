"""
Centralized configuration for trading agents.

Best practices:
- Single source of truth for all configuration
- Environment variables with sensible defaults
- Type-safe configuration values
- Separate configs for dev/prod via env vars
"""

import os
from typing import Optional


class Config:
    """Configuration manager for trading agents."""

    # Backend API Configuration
    BACKEND_BASE_URL: str = os.getenv("BACKEND_URL", "http://backend-service:8080")

    # Derived API endpoints
    @property
    def BACKEND_API_ACCOUNTS(self) -> str:
        """Accounts API endpoint."""
        return f"{self.BACKEND_BASE_URL}/api/accounts"

    @property
    def BACKEND_API_MARKET(self) -> str:
        """Market data API endpoint."""
        return f"{self.BACKEND_BASE_URL}/api/market"

    @property
    def BACKEND_API_RUNS(self) -> str:
        """Run tracking API endpoint (legacy agent runs)."""
        return f"{self.BACKEND_BASE_URL}/api/agent-runs"

    @property
    def BACKEND_API_AGENTS(self) -> str:
        """Agent metadata API endpoint."""
        return f"{self.BACKEND_BASE_URL}/api/agents"

    # Agent Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # MCP Servers Configuration
    BRAVE_API_KEY: str = os.getenv("BRAVE_API_KEY", "")

    # Trading Configuration
    CYCLE_INTERVAL_SECONDS: int = int(os.getenv("CYCLE_INTERVAL_SECONDS", "1800"))  # 30 minutes

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self):
        """Initialize configuration and validate required values."""
        self._validate()

    def _validate(self):
        """Validate that required configuration values are set."""
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        if not self.BRAVE_API_KEY:
            raise ValueError("BRAVE_API_KEY environment variable is required for research functionality")

    def __repr__(self) -> str:
        """String representation (safe - no secrets)."""
        return (
            f"Config(\n"
            f"  BACKEND_BASE_URL={self.BACKEND_BASE_URL}\n"
            f"  OPENAI_MODEL={self.OPENAI_MODEL}\n"
            f"  CYCLE_INTERVAL_SECONDS={self.CYCLE_INTERVAL_SECONDS}\n"
            f"  LOG_LEVEL={self.LOG_LEVEL}\n"
            f")"
        )


# Global configuration instance
# This ensures single source of truth across all modules
config = Config()


# Export commonly used values for convenience
BACKEND_BASE_URL = config.BACKEND_BASE_URL
BACKEND_API_ACCOUNTS = config.BACKEND_API_ACCOUNTS
BACKEND_API_MARKET = config.BACKEND_API_MARKET
BACKEND_API_RUNS = config.BACKEND_API_RUNS
BACKEND_API_AGENTS = config.BACKEND_API_AGENTS
