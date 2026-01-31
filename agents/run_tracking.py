"""
New Trading Runs API functions.

Implements the phase-based tracking workflow:
- create_run(): POST /api/runs
- update_phase(): PATCH /api/runs/{id}/phase
- complete_run(): PUT /api/runs/{id}/complete

Uses BackendClient for centralized HTTP handling.
All functions let exceptions propagate for consistent error handling.
"""

from backend_client import get_backend_client
from models.run_tracking import CompleteRunData


async def create_run(agent_id: int) -> int:
    """Create a new trading run.

    POST /api/runs with {"agentId": agent_id}

    Args:
        agent_id: Backend identifier for the agent

    Returns:
        Run ID from backend

    Raises:
        BackendAPIError: If run creation fails
    """
    client = get_backend_client()
    return await client.create_run(agent_id)


async def update_phase(run_id: int, phase: str) -> None:
    """Update the phase of a trading run.

    PATCH /api/runs/{run_id}/phase with {"phase": phase}

    Args:
        run_id: The run ID to update
        phase: New phase (INITIALIZING, RESEARCHING, DECIDING, TRADING, COMPLETED, ERROR)

    Raises:
        BackendAPIError: If phase update fails
    """
    client = get_backend_client()
    await client.update_phase(run_id, phase)


async def complete_run(run_id: int, data: CompleteRunData) -> None:
    """Complete a trading run with all phase data.

    PUT /api/runs/{run_id}/complete with full CompleteRunData payload.

    Args:
        run_id: The run ID to complete
        data: CompleteRunData containing all phase information

    Raises:
        BackendAPIError: If run completion fails
    """
    client = get_backend_client()
    await client.complete_run(run_id, data)
