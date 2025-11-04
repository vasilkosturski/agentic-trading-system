"""
Status broadcasting for real-time agent updates via WebSocket
"""
import requests
from datetime import datetime
from typing import Optional
from config import BACKEND_BASE_URL
import logging

logger = logging.getLogger(__name__)

# Phase constants
PHASE_INITIALIZING = "INITIALIZING"
PHASE_RESEARCHING = "RESEARCHING"  # Combined: fetching data, research, analysis
PHASE_DECIDING = "DECIDING"
PHASE_TRADING = "TRADING"
PHASE_COMPLETED = "COMPLETED"
PHASE_ERROR = "ERROR"


def broadcast_status(
    agent_id: int,
    agent_name: str,
    phase: str,
    message: str,
    progress: int,
    outcome: Optional[str] = None
) -> None:
    """
    Broadcast agent status update to backend (which forwards to WebSocket clients)
    
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
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Non-blocking request with short timeout (best effort)
        response = requests.post(url, json=payload, timeout=2)
        
        if response.status_code not in [204, 200]:
            logger.warning(f"Status broadcast failed with status {response.status_code}")
            
    except requests.exceptions.Timeout:
        logger.warning(f"Status broadcast timed out for {agent_name}")
    except Exception as e:
        # Never fail trading logic due to status broadcast issues
        logger.warning(f"Failed to broadcast status for {agent_name}: {e}")

