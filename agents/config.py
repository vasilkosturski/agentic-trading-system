"""Centralized configuration for trading agents."""

import os


class Config:
    BACKEND_BASE_URL: str = os.getenv("BACKEND_URL", "http://backend-service:8080")

    @property
    def BACKEND_API_ACCOUNTS(self) -> str:
        return f"{self.BACKEND_BASE_URL}/api/accounts"

    @property
    def BACKEND_API_MARKET(self) -> str:
        return f"{self.BACKEND_BASE_URL}/api/market"

    @property
    def BACKEND_API_TRADING_RUNS(self) -> str:
        return f"{self.BACKEND_BASE_URL}/api/runs"

    @property
    def BACKEND_API_AGENTS(self) -> str:
        return f"{self.BACKEND_BASE_URL}/api/agents"

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5-mini")

    BRAVE_API_KEY: str = os.getenv("BRAVE_API_KEY", "")

    # Admin credentials the agents pod uses to obtain a JWT from
    # POST /api/auth/login before any state-changing backend call.
    BACKEND_ADMIN_USERNAME: str = os.getenv("BACKEND_ADMIN_USERNAME", "admin")
    BACKEND_ADMIN_PASSWORD: str = os.getenv("BACKEND_ADMIN_PASSWORD", "")

    CYCLE_INTERVAL_SECONDS: int = int(os.getenv("CYCLE_INTERVAL_SECONDS", "1800"))

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        if not self.BRAVE_API_KEY:
            raise ValueError(
                "BRAVE_API_KEY environment variable is required for research functionality"
            )

    def __repr__(self) -> str:
        return (
            f"Config(\n"
            f"  BACKEND_BASE_URL={self.BACKEND_BASE_URL}\n"
            f"  OPENAI_MODEL={self.OPENAI_MODEL}\n"
            f"  CYCLE_INTERVAL_SECONDS={self.CYCLE_INTERVAL_SECONDS}\n"
            f"  LOG_LEVEL={self.LOG_LEVEL}\n"
            f")"
        )


config = Config()


BACKEND_BASE_URL = config.BACKEND_BASE_URL
BACKEND_API_ACCOUNTS = config.BACKEND_API_ACCOUNTS
BACKEND_API_MARKET = config.BACKEND_API_MARKET
BACKEND_API_TRADING_RUNS = config.BACKEND_API_TRADING_RUNS
BACKEND_API_AGENTS = config.BACKEND_API_AGENTS
BACKEND_ADMIN_USERNAME = config.BACKEND_ADMIN_USERNAME
BACKEND_ADMIN_PASSWORD = config.BACKEND_ADMIN_PASSWORD
