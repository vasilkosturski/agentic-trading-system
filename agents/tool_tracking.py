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
    """Tracks reasoning steps and tool usage for a run."""

    def __init__(self, run_id: Optional[int]):
        self.run_id = run_id
        self.sequence = 0
        # Track data sources for transparency
        self.tool_calls = []  # List of tool call records
        self.research_queries = []  # Brave Search queries
        self.data_accessed = []  # Database/market data accessed

    def log_tool_call(self, tool_name: str, inputs: dict, output: str):
        """Record a tool call for transparency."""
        self.tool_calls.append({
            "tool": tool_name,
            "inputs": inputs,
            "output": output[:500] if output else "",  # Truncate long outputs
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        logger.debug(f"Tracked tool call: {tool_name} with inputs {inputs}")

    def log_research_query(self, query: str, results_summary: str, sources: list = None):
        """Record a research/search query with sources.

        Args:
            query: The search query performed
            results_summary: Summary of findings
            sources: List of dicts with 'title' and 'url' keys
        """
        self.research_queries.append({
            "query": query,
            "summary": results_summary[:300],  # Truncate
            "sources": sources or [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def log_data_access(self, data_type: str, details: str):
        """Record database or market data access."""
        self.data_accessed.append({
            "type": data_type,
            "details": details[:200],  # Truncate
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def build_reasoning_with_sources(self, base_reasoning: str) -> str:
        """Build rich reasoning text with data sources included."""
        parts = [base_reasoning]

        # Add data accessed section (only for research phase)
        if self.data_accessed:
            parts.append("\n\n📊 Data Context:")
            for item in self.data_accessed:  # All items
                parts.append(f"{item['details']}")

        # Add research section with cleaner format
        if self.research_queries:
            parts.append("\n\n🌐 Market Research:")
            for item in self.research_queries[-2:]:  # Last 2 queries
                # Show summary without the query text
                if item.get('summary'):
                    # Clean up the summary - remove any "Research completed" generic text
                    summary = item['summary']
                    if not summary.startswith('Research completed'):
                        parts.append(summary)

                if item.get('sources'):
                    parts.append("\nSources:")
                    for source in item['sources'][:5]:  # Top 5 sources
                        title = source.get('title', 'Article')
                        url = source.get('url', '')
                        if url:
                            parts.append(f"  • {title} - {url}")

        return "\n".join(parts)

    def log_reasoning(self, step_type: str, description: str, reasoning: str):
        """Log a reasoning step (fire-and-forget)."""
        if not self.run_id:
            return

        self.sequence += 1

        # Enhance reasoning with sources ONLY for research phase
        # Decision phase should NOT include data duplication
        if step_type == "research":
            reasoning = self.build_reasoning_with_sources(reasoning)

        data = {
            "stepType": step_type,
            "stepDescription": description,
            "reasoningText": reasoning,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequenceNumber": self.sequence
        }

        asyncio.create_task(self._send(f"{self.run_id}/reasoning-step", data))

        # Clear tracking data after logging decision (to avoid accumulation across phases)
        if step_type == "decision":
            self.tool_calls = []
            self.research_queries = []
            self.data_accessed = []
    
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
