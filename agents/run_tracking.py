"""
Helper functions for tracking agent runs via backend API.
"""
import json
import httpx
from typing import Optional
import logging

# Import centralized configuration
from config import BACKEND_API_RUNS
from models import MarketConditions

logger = logging.getLogger(__name__)

# Use centralized configuration; already points to /api/runs
BACKEND_URL = BACKEND_API_RUNS


async def start_run(
    agent_id: int,
    agent_name: str,
    run_type: str,
    market_conditions: MarketConditions
) -> Optional[int]:
    """
    Start a new agent run and return the run ID.

    Args:
        agent_id: Backend identifier for the agent
        agent_name: Name of the agent (used for logging only)
        run_type: Type of run (TRADING, REBALANCE)
        market_conditions: MarketConditions with market status

    Returns:
        Run ID if successful, None if failed
    """
    url = f"{BACKEND_URL}/start"

    payload = {
        "agentId": agent_id,
        "runType": run_type,
        "marketConditions": json.dumps({
            "timestamp": market_conditions.timestamp,
            "cycle_type": market_conditions.cycle_type
        })
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
    summary: str,
    full_reasoning: str,
    research_sources: list,
    historical_context: str,
    trade_count: int = 0
) -> bool:
    """
    End an agent run with results.

    Args:
        run_id: The run ID from start_run()
        summary: Brief summary of what happened (simple summary)
        full_reasoning: Complete reasoning/thinking from the agent
        research_sources: List of dicts with research source metadata (web sources)
        historical_context: JSON string with historical insights (past trades, agent context)
        trade_count: Number of trades executed (0 for NO_TRADE)

    Returns:
        True if successful, False if failed
    """
    url = f"{BACKEND_URL}/end"

    payload = {
        "runId": run_id,
        "summary": summary,
        "fullReasoning": full_reasoning,
        "researchSources": json.dumps(research_sources),
        "historicalContext": historical_context,
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
    url = f"{BACKEND_URL}/error"

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
