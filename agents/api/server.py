import asyncio
import logging
import os
from threading import Event, Thread

from flask import Flask, jsonify
from werkzeug.serving import make_server

from logging_config import configure_json_logging

configure_json_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class TradingAPIServer:
    def __init__(
        self,
        trading_system,
        manual_cycle_event: asyncio.Event,
        cycle_running_flag,
        loop: asyncio.AbstractEventLoop,
    ):
        # `loop` is captured explicitly so the Flask handler thread can
        # schedule ``manual_cycle_event.set`` via ``loop.call_soon_threadsafe``
        # without relying on the undocumented ``Event._loop`` attribute.
        self.trading_system = trading_system
        self.manual_cycle_event = manual_cycle_event
        self.cycle_running_flag = cycle_running_flag
        self._loop = loop
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route("/health", methods=["GET"])
        def health():
            return jsonify({"status": "healthy", "service": "trading-agents-api"}), 200

        @self.app.route("/api/trigger-cycle", methods=["POST"])
        def trigger_cycle():
            logger.info("📣 Manual trading cycle requested via API")

            if self.cycle_running_flag["running"]:
                logger.warning("⚠️ Trading cycle already in progress - rejecting duplicate request")
                return jsonify(
                    {
                        "message": "A trading cycle is already in progress. Please wait for it to complete.",
                        "status": "ALREADY_RUNNING",
                    }
                ), 409

            # call_soon_threadsafe on the captured loop hops Event.set() from
            # the Flask handler thread onto the asyncio loop.
            self._loop.call_soon_threadsafe(self.manual_cycle_event.set)
            logger.info("✅ Manual trading cycle triggered successfully")

            return jsonify(
                {"message": "Trading cycle triggered successfully.", "status": "TRIGGERED"}
            ), 202

    def run(self, port=8000):
        # Blocks until the HTTP listener binds (or 5s elapses with a warning).
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
