"""E2E test fixtures with REAL integrations.

These fixtures provide REAL connections to:
- Backend API (PostgreSQL via REST, auto-started via Docker)
- Brave Search API
- OpenAI API

WARNING: Tests using these fixtures cost real $ and make real API calls.

Docker services (postgres + backend) are managed by pytest-docker.
They start automatically on first test and stop after the session.
"""

import os
import logging
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

# Load environment with real API keys
parent_env = Path(__file__).parent.parent.parent.parent / ".env"
if parent_env.exists():
    load_dotenv(parent_env, override=True)
else:
    pytest.skip("No .env file found - E2E tests require real credentials", allow_module_level=True)

# Configure logging for E2E tests (verbose)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
    """Use podman compose instead of docker compose."""
    return "podman compose"


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Point pytest-docker to the E2E compose file."""
    return os.path.join(
        str(pytestconfig.rootdir), "..", "docker-compose.e2e.yml"
    )


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
    import config as config_module
    import market_tools as market_tools_module
    import backend_client as backend_client_module
    import memory_tools as memory_tools_module
    import researcher as researcher_module

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

    memory_tools_module.BACKEND_BASE_URL = url
    researcher_module.BACKEND_BASE_URL = url

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
        # Check if already seeded (idempotent)
        cur.execute(
            "SELECT id FROM agents.trading_agents WHERE name = %s",
            (agent.name,),
        )
        if cur.fetchone():
            logger.info("Test data already seeded — skipping")
            return

        # 1. Agent (omit 'style' — nullable column, may not exist in older backend images)
        cur.execute(
            """
            INSERT INTO agents.trading_agents
                (name, description, is_active, trading_frequency,
                 initial_capital, total_trades, total_pnl, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
            """,
            (agent.name, agent.description, agent.is_active,
             agent.trading_frequency, agent.initial_capital,
             agent.total_trades, agent.total_pnl),
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

        # 4. Agent runs (analytics schema — FK target for account_transactions)
        run_ids = []
        for run in SEED_DATA.agent_runs:
            cur.execute(
                """
                INSERT INTO analytics.agent_runs
                    (agent_name, run_type, start_time, end_time, outcome,
                     summary, full_reasoning, research_sources, trade_count, created_at)
                VALUES
                    (%s, %s,
                     NOW() - INTERVAL '%s days', NOW() - INTERVAL '%s days',
                     %s, %s, %s, %s, %s,
                     NOW() - INTERVAL '%s days')
                RETURNING id
                """,
                (agent.name, run.run_type,
                 run.days_ago, run.days_ago,
                 run.outcome, run.summary, run.full_reasoning,
                 run.research_sources, run.trade_count,
                 run.days_ago),
            )
            run_ids.append(cur.fetchone()[0])

        # 5. Transactions
        for tx in SEED_DATA.transactions:
            run_id = run_ids[tx.run_index]
            days_ago = SEED_DATA.agent_runs[tx.run_index].days_ago
            cur.execute(
                """
                INSERT INTO trading.account_transactions
                    (account_id, symbol, quantity, price, timestamp,
                     agent_run_id, transaction_type, total_amount, created_at)
                VALUES
                    (%s, %s, %s, %s, NOW() - INTERVAL '%s days',
                     %s, %s, %s, NOW() - INTERVAL '%s days')
                """,
                (account_id, tx.symbol, tx.quantity, tx.price, days_ago,
                 run_id, tx.transaction_type, tx.quantity * tx.price, days_ago),
            )

        logger.info(
            f"Seeded test data: agent_id={agent_id}, account_id={account_id}, "
            f"{len(SEED_DATA.holdings)} holdings, {len(run_ids)} runs, "
            f"{len(SEED_DATA.transactions)} transactions"
        )
    finally:
        cur.close()
        conn.close()


# =============================================================================
# Test Agent Configuration (derived from seed_data — single source of truth)
# =============================================================================

@pytest.fixture
def test_agent_id(seed_test_data) -> int:
    """Agent ID for E2E testing.

    Depends on seed_test_data to ensure the agent exists first.
    Uses agent ID 1 (first seeded agent). The dependency on seed_test_data
    ensures the agent is seeded before this fixture returns.
    """
    return 1


@pytest.fixture
def test_agent_name() -> str:
    """Agent name for E2E testing — derived from seed_data."""
    from seed_data import TEST_AGENT
    return TEST_AGENT.name


@pytest.fixture
def test_agent_style() -> str:
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
    """Fetch real holdings from backend."""
    async with real_backend_client.get(f"/api/accounts/{test_agent_id}/holdings") as resp:
        if resp.status == 200:
            data = await resp.json()
            from models import Holding
            return [Holding(**h) for h in data]
        else:
            logger.warning(f"Failed to fetch holdings: {resp.status}")
            return []


@pytest.fixture
async def real_agent_balance(real_backend_client, test_agent_id):
    """Fetch real balance from backend."""
    async with real_backend_client.get(f"/api/accounts/{test_agent_id}/balance") as resp:
        if resp.status == 200:
            return await resp.json()
        else:
            logger.warning(f"Failed to fetch balance: {resp.status}")
            return 0.0


@pytest.fixture
async def real_recent_activity(real_backend_client, test_agent_name):
    """Fetch real recent activity from backend."""
    # Pre-built image uses agentName param; current source uses agentId.
    # Use agentName for compatibility with the deployed image.
    params = {"agentName": test_agent_name, "days": "30"}
    async with real_backend_client.get("/api/memory/recent-activity", params=params) as resp:
        if resp.status == 200:
            data = await resp.json()
            from models.api_responses import RecentActivityResponse
            return RecentActivityResponse(**data)
        else:
            body = await resp.text()
            logger.warning(f"Failed to fetch recent activity: {resp.status} — {body}")
            from models.api_responses import RecentActivityResponse
            return RecentActivityResponse(
                agentName="Warren",
                days=30,
                runs=[],
                totalRuns=0,
                totalTrades=0
            )


# =============================================================================
# Sample Data Fixtures (for smoke tests)
# =============================================================================

@pytest.fixture
def sample_holdings():
    """Sample holdings for smoke tests."""
    from models import Holding
    return [
        Holding(symbol="AAPL", quantity=50, averagePrice=180.0),
        Holding(symbol="MSFT", quantity=30, averagePrice=400.0),
    ]


@pytest.fixture
def sample_recent_activity(test_agent_name):
    """Sample recent activity for smoke tests.

    IMPORTANT: This fixture is synced with sample_holdings.
    The BUY trades here created the positions in sample_holdings.
    Includes realistic research sources to test UI rendering.
    """
    import json
    from datetime import datetime
    from models.api_responses import RecentActivityResponse, ActivityRun, ActivityTrade

    # Realistic research sources for AAPL analysis
    aapl_sources = json.dumps([
        {"type": "web", "title": "Apple Q4 2025 Earnings Report", "url": "https://investor.apple.com/earnings"},
        {"type": "web", "title": "Apple iPhone 16 sales exceed expectations", "url": "https://www.reuters.com/technology/apple-iphone-sales"},
        {"type": "system_context", "description": "Portfolio: $100,000.00, 0 positions"},
    ])

    # Realistic research sources for MSFT analysis
    msft_sources = json.dumps([
        {"type": "web", "title": "Microsoft Azure Revenue Growth Q4 2025", "url": "https://www.microsoft.com/investor"},
        {"type": "web", "title": "Microsoft AI Integration Drives Enterprise Adoption", "url": "https://www.bloomberg.com/news/microsoft-ai"},
        {"type": "system_context", "description": "Portfolio: $91,000.00, 1 position (AAPL)"},
    ])

    return RecentActivityResponse(
        agentName=test_agent_name,
        days=30,
        runs=[
            ActivityRun(
                date=datetime.fromisoformat("2026-01-15T10:00:00"),
                outcome="COMPLETED",
                summary="Bought AAPL based on strong fundamentals",
                fullReasoning="Apple shows strong fundamentals with consistent revenue growth.",
                researchSources=aapl_sources,
                historicalContext=None,
                trades=[
                    ActivityTrade(type="BUY", symbol="AAPL", quantity=50, price=180.0)
                ]
            ),
            ActivityRun(
                date=datetime.fromisoformat("2026-01-20T14:30:00"),
                outcome="COMPLETED",
                summary="Bought MSFT based on cloud growth",
                fullReasoning="Microsoft Azure growth continues to drive revenue.",
                researchSources=msft_sources,
                historicalContext=None,
                trades=[
                    ActivityTrade(type="BUY", symbol="MSFT", quantity=30, price=400.0)
                ]
            ),
        ],
        totalRuns=2,
        totalTrades=2
    )


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
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end (requires real integrations)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (LLM calls)"
    )
    config.addinivalue_line(
        "markers", "costly: mark test as costly (real API calls with billing)"
    )
