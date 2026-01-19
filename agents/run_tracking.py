"""
New Trading Runs API functions.

Implements the phase-based tracking workflow:
- create_run(): POST /api/runs
- update_phase(): PATCH /api/runs/{id}/phase
- complete_run(): PUT /api/runs/{id}/complete

Uses a shared AsyncClient for connection pooling (httpx best practice).
"""

import logging
from typing import Optional

import httpx

from config import BACKEND_API_TRADING_RUNS
from models.run_tracking import CompleteRunData

logger = logging.getLogger(__name__)

# Module-level shared client for connection pooling
# Per httpx docs: "make sure you're not instantiating multiple client instances"
# https://www.python-httpx.org/async/
_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    """Get or create the shared AsyncClient.

    Lazy initialization ensures client is created only when needed.
    Reuses TCP connections across requests for better performance.
    """
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        logger.debug("Created new httpx AsyncClient for run tracking")
    return _client


async def close_client() -> None:
    """Close the shared client. Call during application shutdown."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
        logger.debug("Closed httpx AsyncClient")
    _client = None


async def create_run(agent_id: int) -> Optional[int]:
    """Create a new trading run.

    POST /api/runs with {"agentId": agent_id}

    Args:
        agent_id: Backend identifier for the agent

    Returns:
        Run ID if successful, None if failed
    """
    url = BACKEND_API_TRADING_RUNS
    payload = {"agentId": agent_id}
    client = _get_client()

    try:
        response = await client.post(url, json=payload)
        response.raise_for_status()

        result = response.json()
        run_id = result.get("runId")
        if run_id is not None:
            logger.info(f"Created trading run #{run_id} for agent {agent_id}")
            return run_id
        else:
            logger.error(f"create_run response missing runId: {result}")
            return None

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error creating run: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Error creating run: {e}")
        return None


async def update_phase(run_id: int, phase: str) -> bool:
    """Update the phase of a trading run.

    PATCH /api/runs/{run_id}/phase with {"phase": phase}

    Args:
        run_id: The run ID to update
        phase: New phase (INITIALIZING, RESEARCHING, DECIDING, TRADING, COMPLETED, ERROR)

    Returns:
        True if successful, False if failed
    """
    url = f"{BACKEND_API_TRADING_RUNS}/{run_id}/phase"
    payload = {"phase": phase}
    client = _get_client()

    try:
        response = await client.patch(url, json=payload)
        response.raise_for_status()

        logger.info(f"Updated run #{run_id} to phase {phase}")
        return True

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error updating phase: {e.response.status_code} - {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"Error updating phase: {e}")
        return False


async def complete_run(run_id: int, data: CompleteRunData) -> bool:
    """Complete a trading run with all phase data.

    PUT /api/runs/{run_id}/complete with full CompleteRunData payload.

    Args:
        run_id: The run ID to complete
        data: CompleteRunData containing all phase information

    Returns:
        True if successful, False if failed
    """
    url = f"{BACKEND_API_TRADING_RUNS}/{run_id}/complete"
    payload = data.to_json_dict()
    client = _get_client()

    try:
        response = await client.put(url, json=payload)
        response.raise_for_status()

        logger.info(f"Completed run #{run_id} with decision={data.decision.value}")
        return True

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error completing run: {e.response.status_code} - {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"Error completing run: {e}")
        return False
