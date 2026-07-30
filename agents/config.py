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

    # LiteLLM gateway. When both are set the agents send every LLM call to the
    # gateway and name an *intent* rather than a concrete model; the gateway
    # resolves intent → model/timeout/retries. When unset (local dev) the agents
    # fall back to OPENAI_MODEL and their own key.
    #
    # LLM_GATEWAY_API_KEY is the shared fallback. Each agent prefers its own
    # virtual key from LLM_GATEWAY_KEY_<AGENT> — see infra.model_binding, which
    # owns that lookup because the agent name is only known per call.
    LLM_GATEWAY_BASE_URL: str = os.getenv("LLM_GATEWAY_BASE_URL", "")
    LLM_GATEWAY_API_KEY: str = os.getenv("LLM_GATEWAY_API_KEY", "")

    # Optional dedicated key for the Agents SDK's trace ingest endpoint. Lets
    # tracing survive the gateway cut-over without putting a provider key back
    # in the LLM call path (the gateway does not proxy /v1/traces/ingest).
    OPENAI_TRACING_API_KEY: str = os.getenv("OPENAI_TRACING_API_KEY", "")

    # Intent names must match the ``model_name`` entries in the gateway's
    # model_list. They are deployment facts, so they are env-overridable.
    MODEL_INTENT_RESEARCH: str = os.getenv("MODEL_INTENT_RESEARCH", "research-tier")
    MODEL_INTENT_DECISION: str = os.getenv("MODEL_INTENT_DECISION", "decision-tier")

    # Reasoning effort per phase, explicit rather than implied by a model string.
    RESEARCH_REASONING_EFFORT: str = os.getenv("RESEARCH_REASONING_EFFORT", "low")
    DECISION_REASONING_EFFORT: str = os.getenv("DECISION_REASONING_EFFORT", "medium")

    BRAVE_API_KEY: str = os.getenv("BRAVE_API_KEY", "")

    BACKEND_ADMIN_USERNAME: str = os.getenv("BACKEND_ADMIN_USERNAME", "admin")
    BACKEND_ADMIN_PASSWORD: str = os.getenv("BACKEND_ADMIN_PASSWORD", "")

    CYCLE_INTERVAL_SECONDS: int = int(os.getenv("CYCLE_INTERVAL_SECONDS", "1800"))

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        # Half-configured gateway: a URL with no virtual key sends
        # unauthenticated requests the gateway rejects, and a key with no URL
        # silently falls back to calling the provider directly. Both are
        # deployment mistakes worth failing at startup rather than mid-cycle.
        if self.LLM_GATEWAY_BASE_URL and not self.LLM_GATEWAY_API_KEY:
            raise ValueError(
                "LLM_GATEWAY_API_KEY is required when LLM_GATEWAY_BASE_URL is set "
                "(the gateway rejects unauthenticated requests)"
            )
        if self.LLM_GATEWAY_API_KEY and not self.LLM_GATEWAY_BASE_URL:
            raise ValueError(
                "LLM_GATEWAY_BASE_URL is required when LLM_GATEWAY_API_KEY is set "
                "(a virtual key is only meaningful against the gateway)"
            )

        # One credential path, not both: deployed agents hold a gateway virtual
        # key and no provider key, which is the point of the cut-over. Local dev
        # with no gateway still needs its own provider key.
        gateway_configured = bool(self.LLM_GATEWAY_BASE_URL and self.LLM_GATEWAY_API_KEY)
        if not gateway_configured and not self.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required when no LLM gateway "
                "is configured (set LLM_GATEWAY_BASE_URL + LLM_GATEWAY_API_KEY instead)"
            )

        if not self.BRAVE_API_KEY:
            raise ValueError(
                "BRAVE_API_KEY environment variable is required for research functionality"
            )

    def __repr__(self) -> str:
        # Never interpolate LLM_GATEWAY_API_KEY here — this repr is logged at
        # startup, and the virtual key is a credential.
        return (
            f"Config(\n"
            f"  BACKEND_BASE_URL={self.BACKEND_BASE_URL}\n"
            f"  LLM_GATEWAY_BASE_URL={self.LLM_GATEWAY_BASE_URL or '(direct)'}\n"
            f"  MODEL_INTENT_RESEARCH={self.MODEL_INTENT_RESEARCH}"
            f" (effort={self.RESEARCH_REASONING_EFFORT})\n"
            f"  MODEL_INTENT_DECISION={self.MODEL_INTENT_DECISION}"
            f" (effort={self.DECISION_REASONING_EFFORT})\n"
            f"  OPENAI_MODEL={self.OPENAI_MODEL} (fallback when no gateway)\n"
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
