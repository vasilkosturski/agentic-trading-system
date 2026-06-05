import logging
from dataclasses import dataclass, field
from datetime import datetime

from agents import trace

from agent_executor import AgentExecutor
from config import config
from mcp_helpers.types import MCPPool
from models.investment_style import InvestmentStyle

logger = logging.getLogger(__name__)


async def run_trader_cycle(trader: "SimpleTrader", mcp_pool: MCPPool, force_trade: bool = False):
    try:
        logger.info(f"Starting {trader.name} agent with two-agent architecture...")
        if force_trade:
            logger.info(f"🎯 {trader.name} must make a trade this cycle (manual trigger)")

        trace_name = f"{trader.name}-portfolio-review"
        trace_id = f"trace_{trader.name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        with trace(trace_name, trace_id=trace_id):
            executor = AgentExecutor(
                agent_id=trader.agent_id,
                name=trader.name,
                agent_style=trader.agent_style,
                model_name=trader.model_name,
            )

            await executor.execute_cycle(
                mcp_pool=mcp_pool,
                force_trade=force_trade,
            )

        logger.info(f"{trader.name} agent completed successfully")

    except Exception as e:
        logger.error(f"Error running {trader.name} agent: {e}", exc_info=True)


@dataclass
class SimpleTrader:
    name: str
    agent_style: InvestmentStyle
    strategy: str
    agent_id: int
    model_name: str = field(default_factory=lambda: config.OPENAI_MODEL)

    async def run(self, mcp_pool: MCPPool, force_trade: bool = False):
        await run_trader_cycle(self, mcp_pool, force_trade)
