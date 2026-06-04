#!/usr/bin/env python3
"""
Simple HTTP API server for triggering manual trading cycles.
Runs alongside the continuous trading system using proper encapsulation.
"""

import asyncio
import logging
import os
from threading import Event, Thread

from flask import Flask, jsonify
from werkzeug.serving import make_server

# Ensure JSON logging is installed even when this module is imported in
# isolation (e.g. unit tests). configure_json_logging is idempotent so it's
# a no-op when trading_system.py already ran it.
from logging_config import configure_json_logging

configure_json_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class TradingAPIServer:
    """Encapsulates the Flask API server and its dependencies."""

    def __init__(
        self,
        trading_system,
        manual_cycle_event: asyncio.Event,
        cycle_running_flag,
        loop: asyncio.AbstractEventLoop,
    ):
        """
        Initialize the API server with dependencies.

        Args:
            trading_system: The TradingSystem instance
            manual_cycle_event: asyncio.Event to signal manual cycle triggers
            cycle_running_flag: dict with 'running' boolean to track cycle state
            loop: The asyncio event loop running in the main thread. Captured
                explicitly so the Flask handler thread can schedule
                ``manual_cycle_event.set`` via ``loop.call_soon_threadsafe``
                without relying on the undocumented ``Event._loop`` attribute.
        """
        self.trading_system = trading_system
        self.manual_cycle_event = manual_cycle_event
        self.cycle_running_flag = cycle_running_flag
        self._loop = loop
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route("/health", methods=["GET"])
        def health():
            """Health check endpoint."""
            return jsonify({"status": "healthy", "service": "trading-agents-api"}), 200

        @self.app.route("/api/trigger-cycle", methods=["POST"])
        def trigger_cycle():
            """Trigger a manual trading cycle (demo mode - always allowed)."""
            logger.info("📣 Manual trading cycle requested via API")

            # Check if a cycle is already running
            if self.cycle_running_flag["running"]:
                logger.warning("⚠️ Trading cycle already in progress - rejecting duplicate request")
                return jsonify(
                    {
                        "message": "A trading cycle is already in progress. Please wait for it to complete.",
                        "status": "ALREADY_RUNNING",
                    }
                ), 409  # 409 Conflict

            # Signal the event to trigger a cycle immediately.
            # Use the explicitly-captured loop's call_soon_threadsafe to safely
            # schedule Event.set() from the Flask handler thread onto the
            # asyncio loop running in the main thread.
            self._loop.call_soon_threadsafe(self.manual_cycle_event.set)
            logger.info("✅ Manual trading cycle triggered successfully")

            return jsonify(
                {"message": "Trading cycle triggered successfully.", "status": "TRIGGERED"}
            ), 202  # 202 Accepted - request accepted for processing

    def run(self, port=8000):
        """Run the Flask API server in a daemon thread.

        Blocks the caller until the HTTP listener has bound to the port (or 5s
        elapses, in which case a warning is logged). After this returns the
        /health and /api/trigger-cycle routes are serving.
        """
        ready = Event()

        def run_flask():
            try:
                srv = make_server("0.0.0.0", port, self.app, threaded=True)
                logger.info(f"🌐 Flask listener bound on 0.0.0.0:{port}")
                ready.set()
                srv.serve_forever()
            except Exception as e:
                logger.error(f"❌ Flask server failed to start: {e}", exc_info=True)
                ready.set()

        Thread(target=run_flask, daemon=True).start()
        if not ready.wait(timeout=5.0):
            logger.warning(f"⚠️ Flask listener did not bind within 5s on port {port}")
