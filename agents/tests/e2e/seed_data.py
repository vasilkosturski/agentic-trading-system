"""Typed seed data for E2E tests.

Single source of truth for test data used by both:
- seed_test_data fixture (DB seeding via psycopg2)
- test_agent_* fixtures (agent configuration)

Uses dataclasses for type safety and readability instead of raw SQL strings.
"""

from dataclasses import dataclass, field
from typing import Optional

from models.investment_style import InvestmentStyle


@dataclass(frozen=True)
class SeedAgent:
    """Agent configuration for seeding and test fixtures."""
    name: str
    description: str
    style: InvestmentStyle
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
class SeedTransaction:
    """Historical transaction for seeding."""
    symbol: str
    quantity: int
    price: float
    transaction_type: str


@dataclass(frozen=True)
class SeedData:
    """Complete seed data configuration."""
    agent: SeedAgent
    account: SeedAccount
    holdings: list[SeedHolding]
    transactions: list[SeedTransaction]


# =============================================================================
# THE seed data — single source of truth
# =============================================================================

TEST_AGENT = SeedAgent(
    name="Warren",
    description="Value investing agent",
    style=InvestmentStyle.VALUE,
    model_name="gpt-4o",
)

TEST_ACCOUNT = SeedAccount(balance=50000.0)

TEST_HOLDINGS = [
    SeedHolding(symbol="AAPL", quantity=50, average_price=180.0),
    SeedHolding(symbol="MSFT", quantity=30, average_price=400.0),
]

TEST_TRANSACTIONS = [
    SeedTransaction(symbol="AAPL", quantity=50, price=180.0, transaction_type="BUY"),
    SeedTransaction(symbol="MSFT", quantity=30, price=400.0, transaction_type="BUY"),
    SeedTransaction(symbol="CMCSA", quantity=200, price=30.0, transaction_type="BUY"),
]

SEED_DATA = SeedData(
    agent=TEST_AGENT,
    account=TEST_ACCOUNT,
    holdings=TEST_HOLDINGS,
    transactions=TEST_TRANSACTIONS,
)
