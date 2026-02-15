"""E2E test fixtures with REAL integrations.

These fixtures provide REAL connections to:
- Backend API (PostgreSQL via REST)
- Brave Search API
- OpenAI API

WARNING: Tests using these fixtures cost real $ and make real API calls.
"""

import os
import logging
from pathlib import Path

import pytest
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

def _require_env(var_name: str) -> str:
    """Get required environment variable or skip test."""
    value = os.environ.get(var_name)
    if not value or value.startswith("test-"):
        pytest.skip(f"E2E tests require real {var_name}")
    return value


@pytest.fixture(scope="session")
def openai_api_key() -> str:
    """Real OpenAI API key."""
    return _require_env("OPENAI_API_KEY")


@pytest.fixture(scope="session")
def brave_api_key() -> str:
    """Real Brave Search API key."""
    return _require_env("BRAVE_API_KEY")


@pytest.fixture(scope="session")
def backend_url() -> str:
    """Backend API URL (matches config.py BACKEND_URL env var)."""
    return os.environ.get("BACKEND_URL", "http://localhost:8080")


@pytest.fixture(scope="session")
def require_backend(backend_url) -> str:
    """Verify backend is reachable, skip test if not.

    Quick health check to avoid expensive LLM calls that will fail on tool errors.
    Similar pattern to openai_api_key/brave_api_key early validation.
    """
    import urllib.request
    import urllib.error
    try:
        urllib.request.urlopen(f"{backend_url}/actuator/health", timeout=5)
    except (urllib.error.URLError, OSError):
        pytest.skip(f"Backend not reachable at {backend_url} - skipping E2E test")
    return backend_url


# =============================================================================
# Test Agent Configuration
# =============================================================================

@pytest.fixture
def test_agent_id() -> int:
    """Agent ID for E2E testing.

    Uses agent ID 1 (Warren) by default for consistent testing.
    """
    return 1


@pytest.fixture
def test_agent_name() -> str:
    """Agent name for E2E testing."""
    return "Warren"


@pytest.fixture
def test_agent_style() -> str:
    """Agent style for E2E testing."""
    return "Value Investor"


@pytest.fixture
def test_model_name() -> str:
    """LLM model for E2E testing.

    Uses gpt-4o for better instruction-following.
    Note: gpt-4o-mini struggles with complex multi-step agent workflows.
    """
    return "gpt-4o"


# =============================================================================
# Real Backend API Fixtures
# =============================================================================

@pytest.fixture
async def real_backend_client(backend_url):
    """Real async HTTP client for backend API.

    Uses aiohttp to make real HTTP requests to the backend.
    """
    import aiohttp
    async with aiohttp.ClientSession(base_url=backend_url) as session:
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
    async with real_backend_client.get(f"/api/accounts/{test_agent_id}") as resp:
        if resp.status == 200:
            data = await resp.json()
            from models.api_responses import AccountResponse
            account = AccountResponse.model_validate(data)
            return account.balance
        else:
            logger.warning(f"Failed to fetch balance: {resp.status}")
            return 0.0


@pytest.fixture
async def real_recent_activity(real_backend_client, test_agent_id):
    """Fetch real recent activity from backend."""
    async with real_backend_client.get(f"/api/memory/{test_agent_id}/recent-activity?days=30") as resp:
        if resp.status == 200:
            data = await resp.json()
            from models.api_responses import RecentActivityResponse
            return RecentActivityResponse(**data)
        else:
            logger.warning(f"Failed to fetch recent activity: {resp.status}")
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
