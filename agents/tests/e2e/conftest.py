"""E2E test fixtures with REAL integrations.

These fixtures provide REAL connections to:
- Backend API (PostgreSQL via REST, auto-started via Docker)
- Brave Search API
- OpenAI API

WARNING: Tests using these fixtures cost real $ and make real API calls.

Docker services (postgres + backend) are managed by pytest-docker.
They start automatically on first test and stop after the session.
"""

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import requests
from dotenv import find_dotenv, load_dotenv

if TYPE_CHECKING:
    from models.investment_style import InvestmentStyle

# Ensure common tool directories are on PATH.
# IDE-spawned processes (VSCode, etc.) inherit a minimal PATH that excludes
# /usr/local/bin, /opt/homebrew/bin, /opt/podman/bin, etc.  Extending PATH
# at module level fixes this for ALL subprocesses (pytest-docker, etc.).
_EXTRA_PATH_DIRS = [
    "/usr/local/bin",
    "/opt/homebrew/bin",
    "/opt/podman/bin",
    str(Path.home() / ".local/bin"),  # uv, uvx, pip --user installs
]
_current = os.environ.get("PATH", "")
_missing = [d for d in _EXTRA_PATH_DIRS if d not in _current.split(os.pathsep)]
if _missing:
    os.environ["PATH"] = _current + os.pathsep + os.pathsep.join(_missing)

# Load environment with real API keys.
# find_dotenv walks up the directory tree from this file's location,
# replacing the previous fragile 4x .parent chain.
env_path = find_dotenv(usecwd=False)
if env_path:
    load_dotenv(env_path, override=True)
else:
    raise FileNotFoundError(
        "No .env file found — E2E tests require real credentials. "
        "Expected .env in agentic-trading-system/ (find_dotenv searched upward from conftest.py)."
    )

# Configure logging for E2E tests (verbose)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("e2e_tests")


# =============================================================================
# Environment Validation
# =============================================================================


def _require_env(var_name: str):
    """Skip test if environment variable is missing or a test stub."""
    value = os.environ.get(var_name)
    if not value or value.startswith("test-"):
        pytest.skip(f"E2E tests require real {var_name}")


@pytest.fixture(scope="session")
def require_openai_api_key():
    """Skip if no real OpenAI API key."""
    _require_env("OPENAI_API_KEY")


@pytest.fixture(scope="session")
def require_brave_api_key():
    """Skip if no real Brave Search API key."""
    _require_env("BRAVE_API_KEY")


# =============================================================================
# Docker-based Backend (pytest-docker)
# =============================================================================


@pytest.fixture(scope="session")
def docker_compose_command():
    """Compose command for E2E tests.

    Defaults to Podman locally — its native builder inherits the host CA
    trust store, avoiding BuildKit certificate issues behind corporate
    proxies. CI (GitHub Actions runners ship Docker, not Podman) overrides
    this via the E2E_COMPOSE_COMMAND env var, e.g. "docker compose".
    """
    return os.environ.get("E2E_COMPOSE_COMMAND", "podman compose")


# pytest-docker convention: auto-discovered by name, used by docker_services fixture.
@pytest.fixture(scope="session")
def docker_compose_file():
    """Point pytest-docker to the E2E compose file.

    Uses __file__ for reliable path resolution regardless of pytest rootdir
    (which may be the git repo root rather than the agents/ directory).
    """
    # conftest.py is at agents/tests/e2e/conftest.py
    # docker-compose.e2e.yml is at agentic-trading-system/docker-compose.e2e.yml
    agents_dir = Path(__file__).resolve().parent.parent.parent
    return str(agents_dir.parent / "docker-compose.e2e.yml")


def _is_backend_responsive(url: str) -> bool:
    """Check if backend health endpoint responds."""
    try:
        resp = requests.get(f"{url}/actuator/health", timeout=5)
        return resp.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        return False


@pytest.fixture(scope="session")
def require_backend(docker_ip, docker_services) -> str:
    """Start backend via Docker and wait until healthy.

    Returns the backend base URL for downstream fixtures.
    Uses pytest-docker to auto-start postgres + backend from docker-compose.e2e.yml.

    Also patches module-level URL variables so agent tools (market_tools,
    backend_client) route requests to the Docker backend instead of the
    default localhost:8080.
    """
    port = docker_services.port_for("backend", 8080)
    url = f"http://{docker_ip}:{port}"
    docker_services.wait_until_responsive(
        timeout=120.0,
        pause=2.0,
        check=lambda: _is_backend_responsive(url),
    )
    logger.info(f"Backend ready at {url}")

    # Patch module-level URL variables that were captured at import time.
    # Without this, agent tools try to connect to localhost:8080 instead
    # of the Docker backend's random port.
    import backend.client as backend_client_module
    import config as config_module
    import infra.prompt_loader as prompt_loader_module
    import tools.market_tools as market_tools_module

    config_module.BACKEND_BASE_URL = url
    config_module.BACKEND_API_MARKET = f"{url}/api/market"
    config_module.BACKEND_API_ACCOUNTS = f"{url}/api/accounts"
    config_module.BACKEND_API_TRADING_RUNS = f"{url}/api/runs"
    config_module.BACKEND_API_AGENTS = f"{url}/api/agents"
    config_module.config.BACKEND_BASE_URL = url

    market_tools_module.BACKEND_URL = f"{url}/api/market"

    backend_client_module.BACKEND_BASE_URL = url
    backend_client_module.BACKEND_API_ACCOUNTS = f"{url}/api/accounts"
    backend_client_module.BACKEND_API_TRADING_RUNS = f"{url}/api/runs"

    # prompt_loader captures BACKEND_URL at import time from os.getenv,
    # so patch it directly to route prompt fetches to the Docker backend.
    prompt_loader_module.BACKEND_URL = url

    return url


# =============================================================================
# Database Seeding
# =============================================================================


@pytest.fixture(scope="session")
def seed_test_data(docker_ip, docker_services, require_backend):
    """Seed test data directly into postgres after JPA schema is created.

    Depends on require_backend so that Hibernate has already created the schema
    via ddl-auto: update before we INSERT rows.

    All seed values come from seed_data.SEED_DATA — the single source of truth
    for test data shared between DB seeding and test fixtures.
    """
    import psycopg2
    from seed_data import SEED_DATA

    agent = SEED_DATA.agent

    pg_port = docker_services.port_for("postgres", 5432)
    conn = psycopg2.connect(
        host=docker_ip,
        port=pg_port,
        dbname="agentic_trading",
        user="trading_user",
        password="trading_password",
    )
    conn.autocommit = True
    cur = conn.cursor()

    try:
        # 1. Agent (omit 'style' — nullable column, may not exist in older backend images)
        cur.execute(
            """
            INSERT INTO agents.trading_agents
                (name, description, is_active, trading_frequency,
                 initial_capital, total_trades, total_pnl, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
            """,
            (
                agent.name,
                agent.description,
                agent.is_active,
                agent.trading_frequency,
                agent.initial_capital,
                agent.total_trades,
                agent.total_pnl,
            ),
        )
        agent_id = cur.fetchone()[0]

        # 2. Account
        acct = SEED_DATA.account
        cur.execute(
            """
            INSERT INTO trading.trading_accounts
                (balance, agent_id, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            RETURNING id
            """,
            (acct.balance, agent_id, acct.is_active),
        )
        account_id = cur.fetchone()[0]

        # 3. Holdings
        for h in SEED_DATA.holdings:
            cur.execute(
                """
                INSERT INTO trading.account_holdings
                    (account_id, symbol, quantity, average_price, last_updated, created_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                """,
                (account_id, h.symbol, h.quantity, h.average_price),
            )

        # 4. Transactions (TradingRun created during test execution, not seeded)
        for tx in SEED_DATA.transactions:
            cur.execute(
                """
                INSERT INTO trading.account_transactions
                    (account_id, symbol, quantity, price, timestamp,
                     transaction_type, total_amount, created_at)
                VALUES
                    (%s, %s, %s, %s, NOW() - INTERVAL '10 days',
                     %s, %s, NOW() - INTERVAL '10 days')
                """,
                (
                    account_id,
                    tx.symbol,
                    tx.quantity,
                    tx.price,
                    tx.transaction_type,
                    tx.quantity * tx.price,
                ),
            )

        logger.info(
            f"Seeded test data: agent_id={agent_id}, account_id={account_id}, "
            f"{len(SEED_DATA.holdings)} holdings, "
            f"{len(SEED_DATA.transactions)} transactions"
        )

        return {"agent_id": agent_id, "account_id": account_id}
    finally:
        cur.close()
        conn.close()


# =============================================================================
# Test Agent Configuration (derived from seed_data — single source of truth)
# =============================================================================


@pytest.fixture
def test_agent_id(seed_test_data) -> int:
    """Actual DB-assigned agent ID from seed_test_data.

    Uses the real auto-incremented ID returned by seed_test_data instead of
    a hardcoded value, so tests work even when the DB auto-increment doesn't
    start at 1 (e.g. parallel test sessions sharing the same database).
    """
    return seed_test_data["agent_id"]


@pytest.fixture
def test_agent_name() -> str:
    """Agent name for E2E testing — derived from seed_data."""
    from seed_data import TEST_AGENT

    return TEST_AGENT.name


@pytest.fixture
def test_agent_style() -> "InvestmentStyle":
    """Agent style for E2E testing — derived from seed_data."""
    from seed_data import TEST_AGENT

    return TEST_AGENT.style


@pytest.fixture
def test_model_name() -> str:
    """LLM model for E2E testing — derived from seed_data.

    Uses gpt-4o for better instruction-following.
    Note: gpt-4o-mini struggles with complex multi-step agent workflows.
    """
    from seed_data import TEST_AGENT

    return TEST_AGENT.model_name


# =============================================================================
# Real Backend API Fixtures
# =============================================================================


@pytest.fixture
async def real_backend_client(require_backend):
    """Real async HTTP client for backend API.

    Uses aiohttp to make real HTTP requests to the backend.
    Backend URL comes from require_backend (Docker-managed).
    """
    import aiohttp

    async with aiohttp.ClientSession(base_url=require_backend) as session:
        yield session


@pytest.fixture
async def real_agent_holdings(real_backend_client, test_agent_id):
    """Fetch real holdings from backend via account report."""
    async with real_backend_client.get(f"/api/accounts/resources/accounts/{test_agent_id}") as resp:
        if resp.status == 200:
            data = await resp.json()
            from models import Holding

            return [Holding(**h) for h in data.get("holdings", [])]
        else:
            body = await resp.text()
            pytest.fail(f"Failed to fetch holdings from account report: HTTP {resp.status}\n{body}")


@pytest.fixture
async def real_agent_balance(real_backend_client, test_agent_id):
    """Fetch real balance from backend via account report."""
    async with real_backend_client.get(f"/api/accounts/resources/accounts/{test_agent_id}") as resp:
        if resp.status == 200:
            data = await resp.json()
            return data["balance"]
        else:
            body = await resp.text()
            pytest.fail(f"Failed to fetch balance from account report: HTTP {resp.status}\n{body}")


@pytest.fixture
async def real_recent_activity(real_backend_client, test_agent_id):
    """Fetch real recent activity from backend."""
    params = {"days": "30"}
    async with real_backend_client.get(
        f"/api/accounts/{test_agent_id}/runs/recent-activity", params=params
    ) as resp:
        if resp.status == 200:
            data = await resp.json()
            from models.api_responses import RecentActivityResponse

            return RecentActivityResponse(**data)
        else:
            body = await resp.text()
            pytest.fail(f"Failed to fetch recent activity: HTTP {resp.status}\n{body}")


# =============================================================================
# Real Market Analyst Fixtures
# =============================================================================

# Note: MarketAnalyst requires MCP pool and async creation.
# Use real_mcp_pool fixture + MarketAnalyst.create() in tests directly.


# =============================================================================
# Real Decision Maker Fixtures
# =============================================================================

# Note: DecisionMaker requires async creation with agent_id.
# Use DecisionMaker.create() in tests directly.


# =============================================================================
# Test Markers
# =============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "e2e: mark test as end-to-end (requires real integrations)")
    config.addinivalue_line("markers", "slow: mark test as slow (LLM calls)")
    config.addinivalue_line("markers", "costly: mark test as costly (real API calls with billing)")
