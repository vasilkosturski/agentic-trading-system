import logging

from backend.client import get_backend_client
from models import Holding, TradeResult
from models.api_responses import AccountReport

logger = logging.getLogger(__name__)


async def buy_shares(
    agent_id: int,
    symbol: str,
    quantity: int,
    runId: int | None = None,
    agent_name: str | None = None,
) -> TradeResult:
    who = agent_name or str(agent_id)
    client = get_backend_client()
    result = await client.buy_shares(agent_id, symbol, quantity, run_id=runId)
    logger.info(f"{who} bought {quantity} shares of {symbol}")
    return result


async def sell_shares(
    agent_id: int,
    symbol: str,
    quantity: int,
    runId: int | None = None,
    agent_name: str | None = None,
) -> TradeResult:
    who = agent_name or str(agent_id)
    client = get_backend_client()
    result = await client.sell_shares(agent_id, symbol, quantity, run_id=runId)
    logger.info(f"{who} sold {quantity} shares of {symbol}")
    return result


async def initialize_agent(name: str, initial_balance: float = 100000.0) -> int:
    client = get_backend_client()
    return await client.initialize_agent(name, initial_balance)


async def _get_account_report_raw(agent_id: int) -> AccountReport:
    client = get_backend_client()
    return await client.get_account_report(agent_id)


async def _get_balance_raw(agent_id: int) -> float:
    report = await _get_account_report_raw(agent_id)
    return report.balance


async def _get_holdings_raw(agent_id: int) -> list[Holding]:
    report = await _get_account_report_raw(agent_id)
    return report.holdings
