#!/usr/bin/env python3
"""
Tool call and reasoning step tracking for agent transparency.

This module provides async, fire-and-forget tracking of:
- Every tool call made by the agent (name, input, output, timing)
- Agent's reasoning at each phase of decision-making

Data is sent to the backend API for storage and later display in the UI timeline.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional, Dict
import aiohttp

from config import BACKEND_API_RUNS

logger = logging.getLogger(__name__)


class ToolTracker:
    """Tracks tool calls and reasoning steps for a specific agent run."""
    
    def __init__(self, run_id: Optional[int]):
        """
        Initialize tool tracker for a specific run.
        
        Args:
            run_id: The agent run ID from the backend. If None, tracking will fail silently.
        """
        self.run_id = run_id
        self.sequence_counter = 0
        
    def _next_sequence(self) -> int:
        """Get next sequence number for ordering events."""
        self.sequence_counter += 1
        return self.sequence_counter
    
    async def _send_to_backend(self, endpoint: str, data: Dict[str, Any]) -> None:
        """
        Send data to backend API (fire-and-forget).
        
        Args:
            endpoint: API endpoint path
            data: Payload to send
        """
        if not self.run_id:
            return
            
        try:
            url = f"{BACKEND_API_RUNS}/{self.run_id}/{endpoint}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status not in (200, 201):
                        result = await response.json()
                        logger.warning(f"Failed to track {endpoint}: {result.get('error', 'Unknown error')}")
        except asyncio.TimeoutError:
            logger.warning(f"Timeout tracking {endpoint} for run {self.run_id}")
        except Exception as e:
            logger.warning(f"Error tracking {endpoint} for run {self.run_id}: {e}")
    
    def track_tool_call(
        self,
        tool_name: str,
        input_params: Any,
        output_result: Any,
        duration_ms: int,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """
        Track a tool call (fire-and-forget).
        
        Args:
            tool_name: Name of the tool that was called
            input_params: Input parameters (will be JSON-serialized)
            output_result: Output result (will be JSON-serialized and truncated to 10KB)
            duration_ms: Duration in milliseconds
            success: Whether the call succeeded
            error_message: Error message if failed
        """
        # Serialize input/output
        try:
            input_json = json.dumps(input_params) if not isinstance(input_params, str) else input_params
        except Exception:
            input_json = str(input_params)
        
        try:
            output_json = json.dumps(output_result) if not isinstance(output_result, str) else output_result
        except Exception:
            output_json = str(output_result)
        
        # Truncate output to 10KB
        if len(output_json) > 10240:
            output_json = output_json[:10240] + "... [truncated]"
        
        data = {
            "toolName": tool_name,
            "inputParams": input_json,
            "outputResult": output_json,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "durationMs": duration_ms,
            "success": success,
            "errorMessage": error_message,
            "sequenceNumber": self._next_sequence()
        }
        
        # Fire-and-forget: schedule the request without waiting
        asyncio.create_task(self._send_to_backend("tool-call", data))
    
    def log_reasoning_step(
        self,
        step_type: str,
        step_description: str,
        reasoning_text: str
    ) -> None:
        """
        Log an agent reasoning step (fire-and-forget).
        
        Args:
            step_type: Type of reasoning step (e.g., "research", "analysis", "decision", "execution")
            step_description: Brief description of what agent is doing
            reasoning_text: Detailed agent thoughts/reasoning
        """
        data = {
            "stepType": step_type,
            "stepDescription": step_description,
            "reasoningText": reasoning_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequenceNumber": self._next_sequence()
        }
        
        # Fire-and-forget: schedule the request without waiting
        asyncio.create_task(self._send_to_backend("reasoning-step", data))


def create_tracked_tool(tracker: ToolTracker, tool_func, tool_name: str):
    """
    Wrap a tool function with automatic tracking.
    
    Args:
        tracker: ToolTracker instance
        tool_func: The async tool function to wrap
        tool_name: Name of the tool for tracking
    
    Returns:
        Wrapped tool function that tracks calls
    """
    async def tracked_wrapper(*args, **kwargs):
        start_time = time.time()
        success = True
        error_msg = None
        result = None
        
        try:
            result = await tool_func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            error_msg = str(e)
            raise
        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Prepare input params (combine args and kwargs)
            input_params = {
                "args": args,
                "kwargs": kwargs
            }
            
            # Track the call
            tracker.track_tool_call(
                tool_name=tool_name,
                input_params=input_params,
                output_result=result if success else None,
                duration_ms=duration_ms,
                success=success,
                error_message=error_msg
            )
    
    # Preserve function metadata
    tracked_wrapper.__name__ = tool_func.__name__
    tracked_wrapper.__doc__ = tool_func.__doc__
    
    return tracked_wrapper

