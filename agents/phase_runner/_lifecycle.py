"""Run-tracking + status-broadcast plumbing for one cycle. Private to phase_runner.

Owns the per-cycle sequence: start → transition_to_deciding → transition_to_trading →
complete (or fail). One instance per cycle; agent identity is held on the instance,
``run_id`` flows as an argument so the same shape would survive reuse across cycles.

Failure recording in ``fail`` deliberately swallows cleanup errors so the original
cycle exception never gets masked by a transient broadcast or backend write.
"""

import logging
from typing import Any

import httpx

from backend.client import get_backend_client
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
from infra.exceptions import BackendAPIError
from models.run_tracking import CompleteRunData, RunPhase

logger = logging.getLogger(__name__)


class Lifecycle:
    """Run-tracking protocol for a single trading cycle.

    Holds agent identity only; the backend-assigned ``run_id`` is passed to each
    transition. Backend writes go directly through ``BackendClient`` — there's no
    intermediate forwarding module.
    """

    def __init__(self, agent_id: int, agent_name: str) -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name
        self._client = get_backend_client()

    async def start(self) -> int:
        """Initialize the agent's account, open a run, transition to RESEARCHING.

        Returns the newly-created ``run_id`` from the backend.

        Raises:
            RuntimeError: If ``self.agent_id`` is None/falsy. Agents must come
                from ``TradingSystem.create()`` so the backend assigns the id.
        """
        await self._client.initialize_agent(self.agent_name, 100000.0)

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

        run_id = await self._client.create_run(self.agent_id)
        await self._client.update_phase(run_id, RunPhase.RESEARCHING)

        broadcast_status(
            self.agent_id,
            self.agent_name,
            PHASE_RESEARCHING,
            "Researching market",
            20,
        )

        return run_id

    async def transition_to_deciding(self, run_id: int) -> None:
        await self._client.update_phase(run_id, RunPhase.DECIDING)
        broadcast_status(
            self.agent_id,
            self.agent_name,
            PHASE_DECIDING,
            "Making investment decision",
            70,
        )

    async def transition_to_trading(self, run_id: int) -> None:
        await self._client.update_phase(run_id, RunPhase.TRADING)
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

        The ``outcome_message`` is supplied by the caller because the wording
        depends on ``PhaseStatus`` (COMPLETED / SKIPPED / FAILED).
        """
        await self._client.complete_run(run_id, data)
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

        Logs the error, broadcasts PHASE_ERROR, and if a run exists, marks it
        FAILED via ``update_phase``. Cleanup failures are caught + logged but
        never propagated.
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
                await self._client.update_phase(run_id, RunPhase.FAILED, error_message=error_msg)
            except Exception as cleanup_err:
                logger.error(
                    "run_finalize_failed",
                    extra={
                        "event_type": "run_finalize_failed",
                        "run_id": run_id,
                        "agent_name": self.agent_name,
                        "original_error": str(error),
                        "cleanup_error": str(cleanup_err),
                    },
                )

    async def record_phase_failure(self, run_id: int, phase_kind: str, outcome: Any) -> None:
        """Persist a stub phase-row when the guardrail-retry loop exhausts.

        Best-effort like ``fail`` — transient backend / HTTP / JSON-decode errors
        are logged but never propagated, so the original tripwire exception
        re-raises unobstructed. Programming errors and ``CancelledError`` still
        propagate so bugs and shutdown surface correctly.
        """
        try:
            await self._client.record_phase_failure(run_id, phase_kind, outcome)
        except (BackendAPIError, httpx.HTTPError, ValueError) as persist_err:
            logger.error(
                f"Failed to persist phase-failure stub for run {run_id} ({phase_kind}): {persist_err}"
            )
