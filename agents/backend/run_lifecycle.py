"""Trading-Runs-API + status-broadcast facade for the cycle orchestrator.

`RunLifecycle` encapsulates the run-tracking protocol
(``create_run`` / ``update_phase`` / ``complete_run``) together with the
paired status broadcasts. One instance per agent owns the per-cycle
sequence of:

* ``start`` — initialize agent, open a run, transition to RESEARCHING
* ``transition_to_deciding`` — RESEARCHING → DECIDING
* ``transition_to_trading`` — DECIDING → TRADING
* ``complete`` — record completion + broadcast COMPLETED
* ``fail`` — best-effort failure recording (never raises)

Failure recording in ``fail`` deliberately swallows cleanup errors so the
caller can re-raise the original exception — the one that actually
matters — without it being masked by a transient broadcast or
``update_phase`` failure.
"""

import logging

from backend.run_tracking import complete_run, create_run, update_phase
from backend.status_broadcaster import (
    PHASE_COMPLETED,
    PHASE_DECIDING,
    PHASE_ERROR,
    PHASE_INITIALIZING,
    PHASE_RESEARCHING,
    PHASE_TRADING,
    broadcast_status,
)
from infra.constants import MAX_ERROR_MESSAGE_LEN
from models.run_tracking import CompleteRunData, RunPhase
from tools.trading_tools import initialize_agent

logger = logging.getLogger(__name__)


class RunLifecycle:
    """Trading Runs API + status-broadcast protocol for a single agent.

    Owns the per-cycle sequence of ``create_run`` → phase transitions →
    ``complete_run`` (or FAILED via ``fail``). Holds only agent identity
    (id + name); ``run_id`` is passed as an argument to each transition
    method so the same instance can be reused across cycles without
    carrying stale state.
    """

    def __init__(self, agent_id: int, agent_name: str) -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name

    async def start(self) -> int:
        """Initialize agent account, create run, transition to RESEARCHING.

        Sequence:
          1. ``initialize_agent(agent_name)``
          2. guard: ``agent_id`` must be set
          3. broadcast INITIALIZING
          4. ``run_id = create_run(agent_id)``
          5. ``update_phase(run_id, RESEARCHING)``
          6. broadcast RESEARCHING

        Returns:
            The newly created ``run_id`` from the backend.

        Raises:
            RuntimeError: If ``self.agent_id`` is None/falsy. Agents must
                be created via ``TradingSystem.create()`` so the backend
                assigns an id before this method runs.
        """
        await initialize_agent(self.agent_name)

        if not self.agent_id:
            raise RuntimeError(
                f"Agent id not set for {self.agent_name}. "
                "Use TradingSystem.create() to instantiate."
            )

        broadcast_status(
            self.agent_id,
            self.agent_name,
            PHASE_INITIALIZING,
            "Starting trading cycle",
            0,
        )

        run_id = await create_run(self.agent_id)
        await update_phase(run_id, RunPhase.RESEARCHING)

        broadcast_status(
            self.agent_id,
            self.agent_name,
            PHASE_RESEARCHING,
            "Researching market",
            20,
        )

        return run_id

    async def transition_to_deciding(self, run_id: int) -> None:
        """RESEARCHING → DECIDING phase transition + status broadcast."""
        await update_phase(run_id, RunPhase.DECIDING)
        broadcast_status(
            self.agent_id,
            self.agent_name,
            PHASE_DECIDING,
            "Making investment decision",
            70,
        )

    async def transition_to_trading(self, run_id: int) -> None:
        """DECIDING → TRADING phase transition + status broadcast."""
        await update_phase(run_id, RunPhase.TRADING)
        broadcast_status(
            self.agent_id,
            self.agent_name,
            PHASE_TRADING,
            "Executing trade",
            90,
        )

    async def complete(
        self,
        run_id: int,
        data: CompleteRunData,
        outcome_message: str,
    ) -> None:
        """Complete the run with all phase data and broadcast COMPLETED.

        The ``outcome_message`` is supplied by the caller because the
        wording depends on ``PhaseStatus`` (COMPLETED / SKIPPED / FAILED)
        which lives at the orchestrator layer.
        """
        await complete_run(run_id, data)
        broadcast_status(
            self.agent_id,
            self.agent_name,
            PHASE_COMPLETED,
            outcome_message,
            100,
            outcome=outcome_message,
        )

    async def fail(self, run_id: int | None, error: Exception) -> None:
        """Best-effort failure recording — NEVER raises.

        1. Log the cycle error at ERROR.
        2. Broadcast PHASE_ERROR (best-effort; never raises).
        3. If a run exists, set it to FAILED via ``update_phase``.
           Cleanup failures are caught + logged but never propagated —
           the caller re-raises the ORIGINAL exception, which is the
           one that matters.
        """
        logger.error(f"Cycle error for {self.agent_name}: {error}")

        broadcast_status(
            self.agent_id,
            self.agent_name,
            PHASE_ERROR,
            f"Error: {str(error)}",
            0,
            outcome=f"Failed: {str(error)}",
        )

        if run_id is not None:
            try:
                error_msg = str(error)[:MAX_ERROR_MESSAGE_LEN] or "Unknown error"
                await update_phase(run_id, RunPhase.FAILED, error_message=error_msg)
            except Exception as cleanup_err:
                logger.error(f"Failed to record error state for run {run_id}: {cleanup_err}")
