"""Common pytest fixtures for trading agent tests."""

import os
from unittest.mock import patch

# CRITICAL: Mock environment variables BEFORE any other imports
# This prevents config.py from failing during test collection
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
def sample_holdings() -> List[Dict]:
    """Sample holdings for testing."""
    return [
        {"symbol": "AAPL", "quantity": 100, "averagePrice": 150.0},
        {"symbol": "MSFT", "quantity": 50, "averagePrice": 300.0},
    ]


@pytest.fixture
def sample_account_report(sample_balance, sample_holdings) -> str:
    """Sample account report for testing."""
    holdings_text = "\n".join([
        f"- {h['symbol']}: {h['quantity']} shares @ ${h['averagePrice']:.2f} avg"
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
def sample_decision() -> Dict:
    """Sample trading decision for testing."""
    return {
        "action": "BUY",
        "symbol": "NVDA",
        "quantity": 50,
        "rationale": "Strong AI growth potential",
        "fullReasoning": "NVDA shows strong fundamentals with AI datacenter growth. P/E ratio is reasonable at 40x forward earnings.",
        "researchSources": json.dumps({
            "summary": "NVDA leading in AI chips",
            "sources": [{"title": "NVDA Analysis", "url": "https://example.com/nvda"}]
        }),
        "historicalContext": json.dumps({
            "summary": "No prior NVDA trades",
            "insights": []
        })
    }


@pytest.fixture
def mock_backend_api(mock_aiohttp, sample_balance, sample_holdings, sample_account_report):
    """Mock backend API responses."""
    # Mock common API endpoints
    backend_url = "http://localhost:8080"

    # Balance endpoint
    mock_aiohttp.post(
        f"{backend_url}/tools/get_balance",
        payload=sample_balance,
        repeat=True
    )

    # Holdings endpoint
    mock_aiohttp.post(
        f"{backend_url}/tools/get_holdings",
        payload=sample_holdings,
        repeat=True
    )

    # Account report endpoint
    mock_aiohttp.post(
        f"{backend_url}/tools/get_account_report",
        payload=sample_account_report,
        repeat=True
    )

    # Initialize agent endpoint
    mock_aiohttp.post(
        f"{backend_url}/tools/initialize_agent",
        payload="Agent initialized",
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
    """Mock run tracking functions."""
    start_run = mocker.patch("agent_executor.start_run")
    end_run = mocker.patch("agent_executor.end_run")
    mark_error = mocker.patch("agent_executor.mark_run_as_error")

    start_run.return_value = 123  # Sample run ID

    return {
        "start_run": start_run,
        "end_run": end_run,
        "mark_run_as_error": mark_error,
    }


@pytest.fixture
def mock_tool_tracker(mocker):
    """Mock ToolTracker."""
    mock_class = mocker.patch("agent_executor.ToolTracker")
    mock_instance = MagicMock()
    mock_class.return_value = mock_instance
    return mock_instance
