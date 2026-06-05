import asyncio
import logging
import os
import random
from contextlib import AsyncExitStack

from agents.mcp import MCPServerStdio
from dotenv import load_dotenv

from agent_registry import AGENT_NAMES
from ai_agents.simple_trader import SimpleTrader
from api.server import TradingAPIServer
from backend.client import close_backend_client
from logging_config import configure_json_logging
from mcp_helpers.params import get_mcp_server_params
from mcp_helpers.types import MCPPool
from models.investment_style import InvestmentStyle

load_dotenv(override=True)

_run_interval = os.getenv("RUN_EVERY_N_MINUTES")
if not _run_interval:
    raise ValueError("RUN_EVERY_N_MINUTES environment variable must be set")
RUN_EVERY_N_MINUTES = int(_run_interval)

configure_json_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Investment style + starting balance live at module scope so the
# AGENT_CONFIGS list-comprehension can close over them — list comprehensions
# inside a class body don't see the class's other class-level names.
_AGENT_STYLES = (
    InvestmentStyle.VALUE,
    InvestmentStyle.CONTRARIAN_MACRO,
    InvestmentStyle.RISK_PARITY,
    InvestmentStyle.GROWTH,
)
_DEFAULT_STARTING_BALANCE = 100000.0


class TradingSystem:
    def __init__(self, agents: list[SimpleTrader]):
        self.agents = agents

    AGENT_CONFIGS = [
        {"name": name, "style": style, "balance": _DEFAULT_STARTING_BALANCE}
        for name, style in zip(AGENT_NAMES, _AGENT_STYLES, strict=True)
    ]

    @classmethod
    async def create(cls):
        from backend.client import BackendClient

        client = BackendClient()
        agents = []

        for cfg in cls.AGENT_CONFIGS:
            name, style, balance = cfg["name"], cfg["style"], cfg["balance"]
            try:
                agent_id = await client.initialize_agent(name, balance)
                agents.append(SimpleTrader(name, style, "", agent_id=agent_id))
                logger.info(f"Created {name} ({style}) with agent ID {agent_id}")
            except Exception as e:
                logger.error(f"Failed to initialize agent {name}: {e}")

        if not agents:
            raise RuntimeError("No agents loaded from backend API")

        logger.info(f"✅ TradingSystem created with {len(agents)} agents")
        return cls(agents)

    async def _run_agent_with_own_mcp(self, agent: SimpleTrader, force_trade: bool):
        # Extracted to a method (not an inner closure) so the per-agent runner
        # can be patched in tests for run_all_agents without spinning up real
        # MCP stdio servers.
        async with AsyncExitStack() as stack:
            mcp_params = get_mcp_server_params()
            mcp_pool: MCPPool = {}
            for mcp_name, params in mcp_params.items():
                server = await stack.enter_async_context(
                    MCPServerStdio(params, client_session_timeout_seconds=120)  # type: ignore[arg-type]
                )
                mcp_pool[mcp_name] = server
            logger.info(f"✅ MCP pool created for {agent.name}: {list(mcp_pool.keys())}")
            await agent.run(mcp_pool, force_trade=force_trade)

    async def run_all_agents(self, force_one_trade=False):
        logger.info("🚀 Starting all four autonomous trading agents...")

        self.print_agent_summary()

        forced_agent = None
        if force_one_trade:
            forced_agent = random.choice(self.agents).name
            logger.info(f"🎯 Manual trigger: Forcing {forced_agent} to make a trade this cycle")

        # results is intentionally bound — the zip(self.agents, results) loop
        # below logs per-agent Exception results and tallies cycle metrics.
        tasks = [
            self._run_agent_with_own_mcp(agent, force_trade=(agent.name == forced_agent))
            for agent in self.agents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success = 0
        failure = 0
        for agent, result in zip(self.agents, results, strict=True):
            if isinstance(result, BaseException):
                failure += 1
                logger.error(
                    f"Agent {agent.name} failed during trading cycle: {result!r}",
                    extra={"agent_name": agent.name},
                    exc_info=result,
                )
            else:
                success += 1

        logger.info(
            f"✅ All agents completed their trading cycle (success={success}, failure={failure})"
        )
        return {"success": success, "failure": failure}

    def print_agent_summary(self):
        print("\n" + "=" * 80)
        print("🏛️  AGENTIC TRADING SYSTEM - AGENT ROSTER")
        print("=" * 80)

        for agent in self.agents:
            print(f"👤 {agent.name} ({agent.agent_style})")
            print()

        print("=" * 80 + "\n")


async def run_continuous_trading():
    system = await TradingSystem.create()

    manual_cycle_event = asyncio.Event()

    cycle_running_flag = {"running": False}

    # Capture the running event loop so the Flask handler thread can schedule
    # callbacks back onto it via loop.call_soon_threadsafe rather than
    # reaching into the undocumented asyncio.Event._loop.
    loop = asyncio.get_running_loop()

    api_server = TradingAPIServer(
        trading_system=system,
        manual_cycle_event=manual_cycle_event,
        cycle_running_flag=cycle_running_flag,
        loop=loop,
    )
    api_server.run(port=8000)

    print(f"🔄 Starting scheduler to run every {RUN_EVERY_N_MINUTES} minutes")
    logger.info(f"Continuous trading loop started with {RUN_EVERY_N_MINUTES} minute intervals")
    logger.info("🎓 Demo mode: Trading enabled 24/7 (using end-of-day data)")
    logger.info("📡 Manual cycle trigger available at http://localhost:8000/api/trigger-cycle")
    logger.info(
        f"⏰ First cycle will run in {RUN_EVERY_N_MINUTES} minutes or when manually triggered"
    )
    logger.info(f"🔧 DEBUG: Event loop: {asyncio.get_event_loop()}")
    logger.info(f"🔧 DEBUG: Manual cycle event: {manual_cycle_event}")

    try:
        logger.info("🚀 Entering main trading loop...")
        while True:
            sleep_seconds = RUN_EVERY_N_MINUTES * 60
            logger.info(
                f"💤 Waiting {RUN_EVERY_N_MINUTES} minutes for next cycle (or manual trigger)..."
            )

            is_manual_trigger = False
            try:
                await asyncio.wait_for(manual_cycle_event.wait(), timeout=sleep_seconds)
                logger.info("📣 Manual cycle triggered - starting immediately...")
                manual_cycle_event.clear()
                is_manual_trigger = True
            except TimeoutError:
                logger.info("⏰ Scheduled cycle time reached")

            logger.info("🚀 Starting trading cycle...")

            cycle_running_flag["running"] = True

            try:
                await system.run_all_agents(force_one_trade=is_manual_trigger)
                logger.info("✅ Trading cycle completed.")
            finally:
                cycle_running_flag["running"] = False
                logger.info("🔓 Trading cycle lock released")

    except KeyboardInterrupt:
        logger.info("🛑 Graceful shutdown requested (Ctrl+C)")
        print("\n🛑 Shutting down trading system gracefully...")
    except Exception as e:
        logger.error(f"❌ Trading system error: {e}")
        raise
    finally:
        await close_backend_client()


async def main():
    logger.info("🚀 Starting Agentic Trading System (single run)...")

    try:
        system = await TradingSystem.create()
        await system.run_all_agents()
        logger.info("✅ Trading system completed successfully")
    except Exception as e:
        logger.error(f"❌ Trading system failed: {e}")
        raise
    finally:
        await close_backend_client()


if __name__ == "__main__":
    continuous_mode = os.getenv("CONTINUOUS_MODE", "true").lower() == "true"

    if continuous_mode:
        print("🔄 Running in CONTINUOUS mode")
        asyncio.run(run_continuous_trading())
    else:
        print("🎯 Running in SINGLE mode")
        asyncio.run(main())
