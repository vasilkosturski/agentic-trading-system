"""
Status broadcasting for agent run heartbeats.

Each call POSTs an agent status payload to the backend at
``/api/agents/status``. The backend acknowledges with 204 and logs the
update; nothing further happens server-side. The HTTP call exists so
operators can see in the backend logs which agent is in which phase.

Uses async HTTP to avoid blocking the event loop during broadcasts.
Callers should use asyncio.create_task() for fire-and-forget behavior.
"""

import asyncio
import logging
from datetime import UTC, datetime

import httpx

from config import BACKEND_BASE_URL
from models.run_tracking import RunPhase

logger = logging.getLogger(__name__)

# Phase constants - use enum for type safety, aliases for backward compatibility
PHASE_INITIALIZING = RunPhase.INITIALIZING
PHASE_RESEARCHING = RunPhase.RESEARCHING
PHASE_DECIDING = RunPhase.DECIDING
PHASE_TRADING = RunPhase.TRADING
PHASE_COMPLETED = RunPhase.COMPLETED
PHASE_ERROR = RunPhase.FAILED


async def broadcast_status_async(
    agent_id: int,
    agent_name: str,
    phase: str,
    message: str,
    progress: int,
    outcome: str | None = None,
) -> None:
    """
    Broadcast agent status update to backend (async, non-blocking).

    This function never raises exceptions - status broadcasts should not
    fail the main trading logic.

    Args:
        agent_id: Numeric agent ID
        agent_name: Human-readable agent name
        phase: Current phase (INITIALIZING, RESEARCHING, etc.)
        message: Human-readable status message
        progress: Progress percentage (0-100)
        outcome: Final outcome message (for COMPLETED phase)
    """
    try:
        url = f"{BACKEND_BASE_URL}/api/agents/status"
        payload = {
            "agentId": agent_id,
            "agentName": agent_name,
            "phase": phase,
            "message": message,
            "progress": progress,
            "outcome": outcome,
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }

        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.post(url, json=payload)

            if response.status_code not in [204, 200]:
                logger.warning(f"Status broadcast failed with status {response.status_code}")

    except httpx.HTTPError as e:
        # Never fail trading logic due to HTTP-level status broadcast issues.
        # Narrow to httpx.HTTPError so asyncio.CancelledError and genuine
        # programming errors (e.g. RuntimeError) are not silently swallowed.
        # httpx.TimeoutException is a subclass of HTTPError, so timeouts are
        # still handled here.
        logger.warning(f"Failed to broadcast status for {agent_name}: {e}")


def broadcast_status(
    agent_id: int,
    agent_name: str,
    phase: str,
    message: str,
    progress: int,
    outcome: str | None = None,
) -> None:
    """
    Fire-and-forget status broadcast (convenience wrapper).

    Schedules async broadcast as a background task. Does not block.
    Safe to call from async context without await.

    Args:
        agent_id: Numeric agent ID
        agent_name: Human-readable agent name
        phase: Current phase (INITIALIZING, RESEARCHING, etc.)
        message: Human-readable status message
        progress: Progress percentage (0-100)
        outcome: Final outcome message (for COMPLETED phase)
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(
            broadcast_status_async(agent_id, agent_name, phase, message, progress, outcome)
        )
    except RuntimeError:
        # No running event loop - log and skip (shouldn't happen in normal operation)
        logger.debug(f"No event loop for status broadcast: {agent_name} {phase}")
