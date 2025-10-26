"""
Helper functions for tracking agent runs via backend API.
"""
import json
import httpx
from typing import Optional, Dict, Any
import logging

# Import centralized configuration
from config import BACKEND_API_RUNS

logger = logging.getLogger(__name__)

# Use centralized configuration
BACKEND_URL = BACKEND_API_RUNS


async def start_run(
    agent_name: str,
    run_type: str,
    agent_context: Dict[str, Any],
    market_conditions: Dict[str, Any]
) -> Optional[int]:
    """
    Start a new agent run and return the run ID.

    Args:
        agent_name: Name of the agent (Warren, George, etc.)
        run_type: Type of run (TRADING, REBALANCE)
        agent_context: Dict with portfolio state (cash, holdings, etc.)
        market_conditions: Dict with market status

    Returns:
        Run ID if successful, None if failed
    """
    url = f"{BACKEND_URL}/api/runs/start"

    payload = {
        "agentName": agent_name,
        "runType": run_type,
        "agentContext": json.dumps(agent_context),
        "marketConditions": json.dumps(market_conditions)
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            if result.get("success"):
                run_id = result.get("data")
                logger.info(f"Started run #{run_id} for {agent_name}")
                return run_id
            else:
                error = result.get("error", "Unknown error")
                logger.error(f"Failed to start run: {error}")
                return None

    except Exception as e:
        logger.error(f"Error starting run: {e}")
        return None


async def end_run(
    run_id: int,
    full_reasoning: str,
    research_sources: list,
    summary: str,
    trade_count: int = 0
) -> bool:
    """
    End an agent run with results.

    Args:
        run_id: The run ID from start_run()
        full_reasoning: Complete reasoning/thinking from the agent
        research_sources: List of dicts with research source metadata
        summary: Brief summary of what happened
        trade_count: Number of trades executed (0 for NO_TRADE)

    Returns:
        True if successful, False if failed
    """
    url = f"{BACKEND_URL}/api/runs/end"

    payload = {
        "runId": run_id,
        "fullReasoning": full_reasoning,
        "researchSources": json.dumps(research_sources),
        "summary": summary,
        "tradeCount": trade_count
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            if result.get("success"):
                logger.info(f"Ended run #{run_id}: {result.get('data')}")
                return True
            else:
                error = result.get("error", "Unknown error")
                logger.error(f"Failed to end run: {error}")
                return False

    except Exception as e:
        logger.error(f"Error ending run: {e}")
        return False


async def mark_run_as_error(run_id: int, error_message: str) -> bool:
    """
    Mark a run as failed with error message.

    Args:
        run_id: The run ID from start_run()
        error_message: Error description

    Returns:
        True if successful, False if failed
    """
    url = f"{BACKEND_URL}/api/runs/error"

    payload = {
        "runId": run_id,
        "errorMessage": error_message
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            if result.get("success"):
                logger.info(f"Marked run #{run_id} as error")
                return True
            else:
                error = result.get("error", "Unknown error")
                logger.error(f"Failed to mark run as error: {error}")
                return False

    except Exception as e:
        logger.error(f"Error marking run as error: {e}")
        return False
