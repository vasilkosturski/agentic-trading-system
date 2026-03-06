"""Typed seed data for E2E tests.

Single source of truth for test data used by both:
- seed_test_data fixture (DB seeding via psycopg2)
- test_agent_* fixtures (agent configuration)

Uses dataclasses for type safety and readability instead of raw SQL strings.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SeedAgent:
    """Agent configuration for seeding and test fixtures."""
    name: str
    description: str
    style: str
    model_name: str
    is_active: bool = True
    trading_frequency: str = "DAILY"
    initial_capital: float = 100000.0
    total_trades: int = 2
    total_pnl: float = 0.0


@dataclass(frozen=True)
class SeedAccount:
    """Trading account for seeding."""
    balance: float
    is_active: bool = True


@dataclass(frozen=True)
class SeedHolding:
    """Portfolio holding for seeding."""
    symbol: str
    quantity: int
    average_price: float


@dataclass(frozen=True)
class SeedAgentRun:
    """Historical agent run for seeding."""
    run_type: str
    days_ago: int
    outcome: str
    summary: str
    full_reasoning: str
    research_sources: str
    trade_count: int = 1


@dataclass(frozen=True)
class SeedTransaction:
    """Historical transaction for seeding."""
    symbol: str
    quantity: int
    price: float
    transaction_type: str
    run_index: int  # Index into AGENT_RUNS list to get FK


@dataclass(frozen=True)
class SeedData:
    """Complete seed data configuration."""
    agent: SeedAgent
    account: SeedAccount
    holdings: list[SeedHolding]
    agent_runs: list[SeedAgentRun]
    transactions: list[SeedTransaction]


# =============================================================================
# THE seed data — single source of truth
# =============================================================================

TEST_AGENT = SeedAgent(
    name="Warren",
    description="Value investing agent",
    style="Value Investor",
    model_name="gpt-4o",
)

TEST_ACCOUNT = SeedAccount(balance=50000.0)

TEST_HOLDINGS = [
    SeedHolding(symbol="AAPL", quantity=50, average_price=180.0),
    SeedHolding(symbol="MSFT", quantity=30, average_price=400.0),
]

TEST_AGENT_RUNS = [
    SeedAgentRun(
        run_type="TRADING",
        days_ago=15,
        outcome="COMPLETED",
        summary="Bought AAPL based on strong fundamentals",
        full_reasoning="Apple shows strong fundamentals with consistent revenue growth.",
        research_sources='[{"type":"web","title":"Apple Q4 2025 Earnings","url":"https://investor.apple.com/earnings"}]',
    ),
    SeedAgentRun(
        run_type="TRADING",
        days_ago=10,
        outcome="COMPLETED",
        summary="Bought MSFT based on cloud growth",
        full_reasoning="Microsoft Azure growth continues to drive revenue.",
        research_sources='[{"type":"web","title":"Microsoft Azure Revenue Growth","url":"https://www.microsoft.com/investor"}]',
    ),
    SeedAgentRun(
        run_type="TRADING",
        days_ago=20,
        outcome="COMPLETED",
        summary="Bought CMCSA based on undervaluation and strong cash flow",
        full_reasoning="Comcast trades at P/E of 5.81, well below intrinsic value with robust cash flow generation.",
        research_sources='[{"type":"web","title":"Comcast Q4 2025 Earnings","url":"https://www.cmcsa.com/investor"}]',
    ),
]

TEST_TRANSACTIONS = [
    SeedTransaction(symbol="AAPL", quantity=50, price=180.0, transaction_type="BUY", run_index=0),
    SeedTransaction(symbol="MSFT", quantity=30, price=400.0, transaction_type="BUY", run_index=1),
    SeedTransaction(symbol="CMCSA", quantity=200, price=30.0, transaction_type="BUY", run_index=2),
]

SEED_DATA = SeedData(
    agent=TEST_AGENT,
    account=TEST_ACCOUNT,
    holdings=TEST_HOLDINGS,
    agent_runs=TEST_AGENT_RUNS,
    transactions=TEST_TRANSACTIONS,
)
