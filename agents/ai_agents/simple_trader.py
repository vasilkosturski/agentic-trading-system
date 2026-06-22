import logging
from dataclasses import dataclass, field
from datetime import datetime

from agents import trace

from config import config
from mcp_helpers.types import MCPPool
from models.investment_style import InvestmentStyle
from phase_runner import run_cycle

logger = logging.getLogger(__name__)


async def run_trader_cycle(trader: "SimpleTrader", mcp_pool: MCPPool, force_trade: bool = False):
    logger.info(f"Starting {trader.name} agent with two-agent architecture...")
    if force_trade:
        logger.info(f"🎯 {trader.name} must make a trade this cycle (manual trigger)")

    trace_name = f"{trader.name}-portfolio-review"
    trace_id = f"trace_{trader.name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # run_cycle records its own failures via Lifecycle.fail and never raises,
    # so the previous try/except around it here would only catch programmer errors.
    with trace(trace_name, trace_id=trace_id):
        await run_cycle(
            agent_id=trader.agent_id,
            name=trader.name,
            agent_style=trader.agent_style,
            mcp_pool=mcp_pool,
            model_name=trader.model_name,
            force_trade=force_trade,
        )

    logger.info(f"{trader.name} agent completed")


@dataclass
class SimpleTrader:
    name: str
    agent_style: InvestmentStyle
    strategy: str
    agent_id: int
    model_name: str = field(default_factory=lambda: config.OPENAI_MODEL)

    async def run(self, mcp_pool: MCPPool, force_trade: bool = False):
        await run_trader_cycle(self, mcp_pool, force_trade)
