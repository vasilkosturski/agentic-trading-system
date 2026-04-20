"""Common pytest fixtures for trading agent tests."""

import os
from pathlib import Path
from unittest.mock import patch
from dotenv import load_dotenv

# CRITICAL: Load parent .env FIRST (has real API keys for integration tests)
parent_env = Path(__file__).parent.parent.parent / ".env"
if parent_env.exists():
    load_dotenv(parent_env, override=False)  # Don't override if already set in environment

# THEN set defaults for unit tests (only if not already set by parent .env)
os.environ.setdefault("OPENAI_API_KEY", "test-key-for-unit-tests")
os.environ.setdefault("BACKEND_URL", "http://localhost:8080")  # Matches config.py
os.environ.setdefault("BACKEND_API_ACCOUNTS", "http://localhost:8080")
os.environ.setdefault("BRAVE_API_KEY", "test-brave-key-for-unit-tests")

import json
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest
from aioresponses import aioresponses

# Import models for fixtures
from models import TradingDecision, Holding
from models.investment_style import InvestmentStyle


@pytest.fixture
def mock_aiohttp():
    """Mock aiohttp client responses."""
    with aioresponses() as m:
        yield m


@pytest.fixture
def sample_agent_id() -> int:
    """Sample agent ID for testing."""
    return 1


@pytest.fixture
def sample_agent_name() -> str:
    """Sample agent name for testing."""
    return "Warren"


@pytest.fixture
def sample_agent_style() -> InvestmentStyle:
    """Sample agent style for testing (two-agent architecture)."""
    return InvestmentStyle.VALUE


@pytest.fixture
def sample_model_name() -> str:
    """Sample model name for testing."""
    return "gpt-4o-mini"


@pytest.fixture
def sample_strategy() -> str:
    """Sample investment strategy for testing."""
    return """Value investing strategy focused on:
- Strong fundamentals (P/E < 20, ROE > 15%)
- Competitive moats and pricing power
- Long-term hold mentality (5+ years)
- Focus on quality businesses at reasonable prices"""


@pytest.fixture
def sample_balance() -> float:
    """Sample account balance for testing."""
    return 100000.0


@pytest.fixture
def sample_holdings() -> List[Holding]:
    """Sample holdings for testing (as Holding objects)."""
    return [
        Holding(symbol="AAPL", quantity=100, averagePrice=150.0),
        Holding(symbol="MSFT", quantity=50, averagePrice=300.0),
    ]


@pytest.fixture
def sample_account_report(sample_balance, sample_holdings) -> str:
    """Sample account report for testing.

    Financial story: Agent started with $130K, bought $30K of stock (AAPL + MSFT),
    leaving $100K cash. Total portfolio = cash + stock value = $130K.
    """
    holdings_text = "\n".join([
        f"- {h.symbol}: {h.quantity} shares @ ${h.averagePrice:.2f} avg"
        for h in sample_holdings
    ])
    stock_value = sum(h.quantity * h.averagePrice for h in sample_holdings)
    return f"""Account: Warren
Balance: ${sample_balance:,.2f}
Holdings:
{holdings_text}
Total Portfolio Value: ${sample_balance + stock_value:,.2f}"""


@pytest.fixture
def sample_recent_activity():
    """Sample recent activity for testing (typed Pydantic model).

    IMPORTANT: This fixture is synced with sample_holdings.
    The BUY trades here created the positions in sample_holdings.
    """
    from models.api_responses import RecentActivityResponse, ActivityRun, ActivityTrade
    return RecentActivityResponse(
        agentName="Warren",
        days=30,
        runs=[
            ActivityRun(
                date="2025-12-10T10:00:00Z",
                outcome="COMPLETED",
                summary="Bought AAPL based on strong fundamentals",
                fullReasoning="Apple shows strong fundamentals with consistent revenue growth.",
                researchSources=None,
                historicalContext=None,
                trades=[
                    ActivityTrade(type="BUY", symbol="AAPL", quantity=100, price=150.0)
                ]
            ),
            ActivityRun(
                date="2025-12-15T14:30:00Z",
                outcome="COMPLETED",
                summary="Bought MSFT based on cloud growth",
                fullReasoning="Microsoft Azure growth continues to drive revenue.",
                researchSources=None,
                historicalContext=None,
                trades=[
                    ActivityTrade(type="BUY", symbol="MSFT", quantity=50, price=300.0)
                ]
            )
        ],
        totalRuns=2,
        totalTrades=2
    )


@pytest.fixture
def sample_decision() -> TradingDecision:
    """Sample trading decision for testing."""
    return TradingDecision(
        action="BUY",
        symbol="NVDA",
        quantity=50,
        rationale="Strong AI growth potential",
        portfolioContext="Currently hold 2/10 positions (AAPL, MSFT) with $100K available cash. Adding NVDA diversifies into AI infrastructure.",
        historicalContext="No prior NVDA trades in portfolio. First entry into semiconductor sector.",
        researchContext="Research highlights NVDA as top AI infrastructure play. P/E ratio is reasonable at 40x forward earnings with strong datacenter growth.",
    )


@pytest.fixture
def sample_research_response():
    """Sample research response from Market Analyst for testing (two-agent architecture)."""
    from models.llm_output import ResearchResponse, WebSource, CandidateStock
    return ResearchResponse(
        summary="Found 3 value stocks: JPM, BAC, WFC. All show strong fundamentals with P/E ratios under 15 and solid dividend yields.",
        candidates=[
            CandidateStock(symbol="JPM", price=195.50),
            CandidateStock(symbol="BAC", price=42.30),
            CandidateStock(symbol="WFC", price=58.75),
        ],
        webSources=[
            WebSource(title="JPMorgan Q4 Earnings Beat Expectations", url="https://example.com/jpm-earnings"),
            WebSource(title="Bank Sector Analysis 2025", url="https://example.com/bank-analysis"),
            WebSource(title="Wells Fargo Recovery Story", url="https://example.com/wfc-recovery"),
        ]
    )


@pytest.fixture
def mock_mcp_pool():
    """Mock MCP pool for two-agent architecture testing.

    Returns a dict with mock servers keyed by MCPName.
    """
    from mcp_types import MCPName
    return {
        MCPName.BRAVE_SEARCH: MagicMock(),
        MCPName.FETCH: MagicMock(),
    }


@pytest.fixture
def mock_backend_api(mock_aiohttp, sample_balance, sample_holdings, sample_account_report, sample_agent_id):
    """Mock backend API responses using REST endpoints.

    Uses the unified account report endpoint (AccountReportDto) for balance
    and holdings data instead of the deleted separate endpoints.
    """
    # Mock common API endpoints
    backend_url = "http://localhost:8080"

    # Account report endpoint - GET /api/accounts/resources/accounts/{agentId}
    # Returns balance, holdings, and portfolio metrics in a single call.
    mock_aiohttp.get(
        f"{backend_url}/api/accounts/resources/accounts/{sample_agent_id}",
        payload={
            "agentName": "Warren",
            "balance": sample_balance,
            "holdings": [h.dict() for h in sample_holdings],
            "holdingsValue": sum(h.quantity * h.averagePrice for h in sample_holdings),
            "totalPortfolioValue": sample_balance + sum(h.quantity * h.averagePrice for h in sample_holdings),
            "initialBalance": 130000.0,
            "totalProfitLoss": 0.0,
            "profitLossPercent": 0.0,
            "holdingsCount": len(sample_holdings),
            "transactionCount": 2,
        },
        repeat=True
    )

    # Initialize agent endpoint - POST /
    mock_aiohttp.post(
        f"{backend_url}/",
        payload={"id": sample_agent_id, "name": "Warren", "balance": sample_balance},
        repeat=True
    )

    # Buy/sell trades endpoint - POST /{agentId}/trades
    mock_aiohttp.post(
        f"{backend_url}/{sample_agent_id}/trades",
        payload="Trade executed successfully",
        repeat=True
    )

    return mock_aiohttp


@pytest.fixture
def mock_mcp_servers():
    """Mock MCP server list for researcher."""
    return []


@pytest.fixture
def mock_runner():
    """Mock OpenAI Agents SDK Runner."""
    mock = AsyncMock()
    mock.run = AsyncMock()
    return mock


@pytest.fixture
def mock_agent():
    """Mock OpenAI Agent."""
    mock = MagicMock()
    mock.name = "TestAgent"
    return mock


@pytest.fixture
def mock_broadcast_status(mocker):
    """Mock status broadcasting."""
    return mocker.patch("agent_executor.broadcast_status")


@pytest.fixture
def mock_prompt_fetch(mocker):
    """Mock httpx.get in prompt_loader so agent-creation tests don't need a real backend.

    PURPOSE:
    --------
    Unit tests need to create agents (Market Analyst, Decision Maker) to verify
    their configuration without requiring a running backend. This fixture patches
    prompt_loader.httpx.get to return a synthetic prompt instead of making real
    HTTP calls to http://localhost:8080/api/prompts/...

    WHY NOT autouse=True:
    ---------------------
    This fixture is DELIBERATELY NOT autouse=True. Making it autouse would apply
    the mock to ALL tests including E2E and integration tests that NEED real HTTP
    calls to verify the full system end-to-end. That would break E2E tests.

    USAGE PATTERN (explicit request):
    ---------------------------------
    Unit tests that need this mock MUST explicitly request it in their test signature:

        async def test_create_agent(mock_prompt_fetch):  # <- explicitly requests fixture
            agent = await create_market_analyst_agent(...)
            # Agent is created without hitting real backend

    E2E tests that need real HTTP calls should NOT request this fixture:

        @pytest.mark.e2e
        async def test_full_cycle_e2e():  # <- NO mock_prompt_fetch parameter
            # Makes real HTTP calls to backend
            agent = await create_market_analyst_agent(...)

    SCOPE:
    ------
    Function scope (default). Each test that requests this fixture gets isolated
    mock state. The patch is applied ONLY to tests that explicitly request the
    fixture via their parameter list.

    CURRENT USAGE:
    --------------
    - 6 unit tests explicitly request this fixture (4 in test_market_analyst.py,
      2 in test_decision_maker.py)
    - 3 E2E tests do NOT use this fixture (all tests in tests/e2e/)
    - E2E tests make real HTTP calls and require a running backend

    IMPLEMENTATION DETAILS:
    -----------------------
    The production code path hits http://localhost:8080/api/prompts/... via
    prompt_loader.load_composed_prompt(). This fixture returns a synthetic prompt
    template so tests can create agents without a running backend.

    The template includes the literal agent name "Warren" (matches sample_agent_name)
    so `assert sample_agent_name in agent.instructions` passes. Production code only
    passes {datetime} and {position_sizing_pct} as kwargs — any other placeholder
    is preserved by prompt_loader._PartialFormatDict.
    """
    mock_response = MagicMock()
    mock_response.text = (
        "You are Warren, a disciplined investor. "
        "Current time: {datetime}. "
        "Position sizing: {position_sizing_pct}%."
    )
    mock_response.raise_for_status = MagicMock()
    return mocker.patch("prompt_loader.httpx.get", return_value=mock_response)


@pytest.fixture
def mock_run_tracking(mocker):
    """Mock run tracking functions (new phase-based API)."""
    create_run = mocker.patch("agent_executor.create_run")
    update_phase = mocker.patch("agent_executor.update_phase")
    complete_run = mocker.patch("agent_executor.complete_run")

    # create_run returns run_id, update_phase/complete_run return bool
    create_run.return_value = 123  # Sample run ID
    update_phase.return_value = True
    complete_run.return_value = True

    return {
        "create_run": create_run,
        "update_phase": update_phase,
        "complete_run": complete_run,
    }


@pytest.fixture
def mock_tool_tracker(mocker):
    """Mock ToolTracker."""
    mock_class = mocker.patch("agent_executor.ToolTracker")
    mock_instance = MagicMock()
    mock_class.return_value = mock_instance
    return mock_instance


# =============================================================================
# Researcher Test Fixtures
# =============================================================================


@pytest.fixture
def mock_backend_response():
    """Factory fixture for creating mock backend HTTP responses.
    
    Usage:
        response = mock_backend_response({"key": "value"})
        # response.text is the JSON-encoded data
    """
    def _create(data: dict) -> MagicMock:
        mock = MagicMock()
        mock.text = json.dumps(data)
        return mock
    return _create


@pytest.fixture
def valid_holdings_data():
    """Valid holdings response data for researcher tests."""
    return {
        "agentName": "Warren",
        "balance": 10000.0,
        "holdings": [],
        "positionCount": 0
    }


@pytest.fixture
def valid_recent_activity_data():
    """Valid recent activity response data for researcher tests."""
    return {
        "agentName": "Warren",
        "days": 30,
        "runs": [],
        "totalRuns": 0,
        "totalTrades": 0
    }


@pytest.fixture
def empty_recent_activity():
    """Empty recent activity for testing (typed Pydantic model)."""
    from models.api_responses import RecentActivityResponse
    return RecentActivityResponse(
        agentName="Warren",
        days=30,
        runs=[],
        totalRuns=0,
        totalTrades=0
    )


@pytest.fixture
def valid_symbol_history_data():
    """Valid symbol history response data for researcher tests."""
    return {
        "symbol": "AAPL",
        "agentName": "Warren",
        "days": 30,
        "currentPosition": None,
        "trades": [],
        "summary": None
    }
