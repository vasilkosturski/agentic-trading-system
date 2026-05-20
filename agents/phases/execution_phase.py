"""Execution phase — dispatches a BUY or SELL trade.

Extracted from ``AgentExecutor._execute_trade`` (Task 8 of the
agent-executor decomposition plan at
``docs/superpowers/plans/2026-05-13-aegr-decomposition.md``). Mirror of
``phases/research_phase.py`` (Task 6) and ``phases/decision_phase.py``
(Task 7) — the closer precedent is decision_phase because it, too, takes
the ``RunLifecycle`` and drives a persisted phase transition at the top.

HOLD is filtered by the caller in ``agent_executor.execute_cycle`` —
this function only handles BUY/SELL. The agent name is threaded as an
explicit parameter so the function stays self-less (the original method
read ``self.name`` for the ``agent_name`` argument to the trading tool
calls).
"""

import logging

from models import TradingDecision
from models.orchestration import ExecutionResult
from models.run_tracking import PhaseStatus, TradeDecision
from backend.run_lifecycle import RunLifecycle
from tools.trading_tools import buy_shares, sell_shares

logger = logging.getLogger(__name__)


async def run_execution_phase(
    run_id: int,
    agent_id: int,
    agent_name: str,
    decision: TradingDecision,
    lifecycle: RunLifecycle,
) -> ExecutionResult:
    """Execute BUY/SELL decision. HOLD is filtered by caller in execute_cycle.

    Args:
        run_id: Run ID for tracking
        agent_id: Agent ID for trading
        agent_name: Agent name (threaded into trading-tool calls; was
            ``self.name`` in the original method).
        decision: Trading decision to execute (must be BUY or SELL)
        lifecycle: RunLifecycle instance driving phase transitions

    Returns:
        ExecutionResult with execution results

    Side effect:
        Calls ``lifecycle.transition_to_trading(run_id)`` at the top to
        advance the run's persisted phase.
    """
    action = decision.action
    symbol = decision.symbol
    quantity = decision.quantity

    logger.info(f"✅ Validated decision: {action} {symbol or ''}")
    logger.info(f"🟡 ABOUT TO EXECUTE: decision={decision}")
    logger.info(f"🟢 EXECUTING: {action} {quantity} shares of {symbol}")

    await lifecycle.transition_to_trading(run_id)

    trade_id = None
    execution_status: PhaseStatus
    execution_error: str | None = None

    try:
        if action == TradeDecision.BUY:
            result = await buy_shares(
                agent_id,
                symbol,
                quantity,
                runId=run_id,
                agent_name=agent_name,
            )
        else:  # SELL
            result = await sell_shares(
                agent_id,
                symbol,
                quantity,
                runId=run_id,
                agent_name=agent_name,
            )
        execution_status = PhaseStatus.COMPLETED
        trade_id = result.tradeId
    except Exception as trade_err:
        logger.error(f"Trade execution failed: {trade_err}")
        execution_status = PhaseStatus.FAILED
        execution_error = str(trade_err)

    return ExecutionResult(
        execution_status=execution_status,
        trade_id=trade_id,
        execution_error=execution_error,
    )
