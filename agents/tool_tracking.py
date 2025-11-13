#!/usr/bin/env python3
"""
Simple reasoning tracking for agent transparency.
Fire-and-forget logging to backend API.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional
import aiohttp

from config import BACKEND_API_RUNS

logger = logging.getLogger(__name__)


class ToolTracker:
    """Tracks reasoning steps for a run."""
    
    def __init__(self, run_id: Optional[int]):
        self.run_id = run_id
        self.sequence = 0
    
    def log_reasoning(self, step_type: str, description: str, reasoning: str):
        """Log a reasoning step (fire-and-forget)."""
        if not self.run_id:
            return
        
        self.sequence += 1
        
        data = {
            "stepType": step_type,
            "stepDescription": description,
            "reasoningText": reasoning,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequenceNumber": self.sequence
        }
        
        asyncio.create_task(self._send(f"{self.run_id}/reasoning-step", data))
    
    async def _send(self, endpoint: str, data: dict):
        """Send to backend (internal use only)."""
        try:
            url = f"{BACKEND_API_RUNS}/{endpoint}"
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status not in (200, 201):
                        result = await response.json()
                        logger.warning(f"Tracking failed: {result.get('error', 'Unknown')}")
        except asyncio.TimeoutError:
            logger.warning(f"Tracking timeout for run {self.run_id}")
        except Exception as e:
            logger.warning(f"Tracking error: {e}")
