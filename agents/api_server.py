#!/usr/bin/env python3
"""
Simple HTTP API server for triggering manual trading cycles.
Runs alongside the continuous trading system using proper encapsulation.
"""

import asyncio
import logging
from flask import Flask, jsonify
from threading import Thread

logger = logging.getLogger(__name__)


class TradingAPIServer:
    """Encapsulates the Flask API server and its dependencies."""
    
    def __init__(self, trading_system, check_market_status_func, manual_cycle_event):
        """
        Initialize the API server with dependencies.
        
        Args:
            trading_system: The TradingSystem instance
            check_market_status_func: Async function to check if market is open
            manual_cycle_event: asyncio.Event to signal manual cycle triggers
        """
        self.trading_system = trading_system
        self.check_market_status_func = check_market_status_func
        self.manual_cycle_event = manual_cycle_event
        self.app = Flask(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint."""
            return jsonify({"status": "healthy", "service": "trading-agents-api"}), 200
        
        @self.app.route('/api/trigger-cycle', methods=['POST'])
        def trigger_cycle():
            """Trigger a manual trading cycle."""
            # Check market status before triggering
            try:
                # Run the async market check in a new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                is_market_open = loop.run_until_complete(self.check_market_status_func())
                loop.close()
                
                if not is_market_open:
                    logger.info("📣 Manual cycle requested but market is closed")
                    # Return 409 Conflict - operation cannot be performed in current state
                    return jsonify({
                        "error": "Market is currently closed. Trading cycles only run when the market is open.",
                        "reason": "MARKET_CLOSED"
                    }), 409
            except Exception as e:
                logger.error(f"Error checking market status: {e}")
                # This is an actual error - return 500
                return jsonify({
                    "error": f"Failed to check market status: {str(e)}",
                    "reason": "SERVICE_ERROR"
                }), 500
            
            # Signal the event to trigger a cycle immediately
            # Use call_soon_threadsafe to safely signal from Flask thread to async loop
            self.manual_cycle_event._loop.call_soon_threadsafe(self.manual_cycle_event.set)
            logger.info("📣 Manual trading cycle triggered via API - market is open")
            
            return jsonify({
                "message": "Trading cycle triggered successfully.",
                "status": "TRIGGERED"
            }), 202  # 202 Accepted - request accepted for processing
    
    def run(self, port=8000):
        """Run the Flask API server in a separate daemon thread."""
        def run_flask():
            try:
                logger.info(f"🚀 Starting Flask server on 0.0.0.0:{port}")
                self.app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)
            except Exception as e:
                logger.error(f"❌ Flask server failed to start: {e}", exc_info=True)
        
        thread = Thread(target=run_flask, daemon=True)
        thread.start()
        logger.info(f"🌐 API server thread started on port {port}")
        
        # Give Flask a moment to start
        import time
        time.sleep(2)
        logger.info(f"✅ Flask server should be running on http://0.0.0.0:{port}")
