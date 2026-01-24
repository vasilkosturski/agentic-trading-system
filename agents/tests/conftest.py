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
os.environ.setdefault("BACKEND_BASE_URL", "http://localhost:8080")
os.environ.setdefault("BACKEND_API_ACCOUNTS", "http://localhost:8080")
os.environ.setdefault("BRAVE_API_KEY", "test-brave-key-for-unit-tests")

import asyncio
import json
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest
from aioresponses import aioresponses

# Import models for fixtures
from models import TradingDecision, Holding


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
def sample_agent_style() -> str:
    """Sample agent style for testing (two-agent architecture)."""
    return "Value Investor"


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
    """Sample account report for testing."""
    holdings_text = "\n".join([
        f"- {h.symbol}: {h.quantity} shares @ ${h.averagePrice:.2f} avg"
        for h in sample_holdings
    ])
    return f"""Account: Warren
Balance: ${sample_balance:,.2f}
Holdings:
{holdings_text}
Total Portfolio Value: ${sample_balance + 15000 + 15000:,.2f}"""


@pytest.fixture
def sample_recent_activity() -> str:
    """Sample recent activity JSON for testing."""
    return json.dumps({
        "runs": [
            {
                "runId": 1,
                "runType": "TRADING",
                "timestamp": "2025-12-10T10:00:00Z",
                "trades": [
                    {"symbol": "NVDA", "action": "BUY", "quantity": 50, "price": 145.0}
                ],
                "reasoning": "AI growth thesis"
            }
        ]
    })


@pytest.fixture
def sample_decision() -> TradingDecision:
    """Sample trading decision for testing."""
    return TradingDecision(
        action="BUY",
        symbol="NVDA",
        quantity=50,
        rationale="Strong AI growth potential",
        fullReasoning="NVDA shows strong fundamentals with AI datacenter growth. P/E ratio is reasonable at 40x forward earnings.",
        researchSources=json.dumps({
            "summary": "NVDA leading in AI chips",
            "sources": [{"title": "NVDA Analysis", "url": "https://example.com/nvda"}]
        }),
        historicalContext=json.dumps({
            "summary": "No prior NVDA trades",
            "insights": []
        })
    )


@pytest.fixture
def sample_research_response():
    """Sample research response from Market Analyst for testing (two-agent architecture)."""
    from models.llm_output import ResearchResponse, ResearchSource
    return ResearchResponse(
        summary="Found 3 value stocks: JPM, BAC, WFC. All show strong fundamentals with P/E ratios under 15 and solid dividend yields.",
        candidates=["JPM", "BAC", "WFC"],
        sources=[
            ResearchSource(title="JPMorgan Q4 Earnings Beat Expectations", url="https://example.com/jpm-earnings"),
            ResearchSource(title="Bank Sector Analysis 2025", url="https://example.com/bank-analysis"),
            ResearchSource(title="Wells Fargo Recovery Story", url="https://example.com/wfc-recovery"),
        ]
    )


@pytest.fixture
def mock_mcp_pool():
    """Mock MCP pool for two-agent architecture testing."""
    pool = MagicMock()
    pool.get_server = AsyncMock(return_value=MagicMock())  # Returns mock MCP server
    return pool


@pytest.fixture
def mock_backend_api(mock_aiohttp, sample_balance, sample_holdings, sample_account_report, sample_agent_id):
    """Mock backend API responses using new REST endpoints."""
    # Mock common API endpoints
    backend_url = "http://localhost:8080"

    # Balance endpoint - GET /{agentId}/balance
    mock_aiohttp.get(
        f"{backend_url}/{sample_agent_id}/balance",
        payload=sample_balance,
        repeat=True
    )

    # Holdings endpoint - GET /{agentId}/holdings
    mock_aiohttp.get(
        f"{backend_url}/{sample_agent_id}/holdings",
        payload=[h.dict() for h in sample_holdings],  # Convert Holding objects to dicts
        repeat=True
    )

    # Account report endpoint - GET /resources/accounts/{agentId}
    mock_aiohttp.get(
        f"{backend_url}/resources/accounts/{sample_agent_id}",
        payload=sample_account_report,
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
