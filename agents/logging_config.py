"""
Centralized JSON logging configuration for the agents service.

Why JSON: log shippers (Grafana Alloy, Promtail, Fluent Bit) extract structured
fields directly from a JSON envelope instead of regex-matching free-form message
text. The Loki `level` label is then read from an explicit field rather than
inferred from whatever substring happens to start the line, which is fragile
for multi-line tracebacks, ISO-formatted timestamps, and werkzeug access logs.

Each emitted line is a single-line JSON object with at least:
    {"timestamp": "...", "level": "INFO", "logger": "...", "message": "..."}

Werkzeug's request-handler logger is reattached to the same JSON formatter so
its access-log lines (e.g. `127.0.0.1 - - [...] "GET /health" 200 -`) flow
through the same envelope rather than escaping as plain text.
"""

from __future__ import annotations

import logging
import sys

from pythonjsonlogger.json import JsonFormatter

_CONFIGURED = False


class _StableJsonFormatter(JsonFormatter):
    """JsonFormatter that always emits the canonical key set.

    The base class only writes a field if either the record has a non-empty
    value OR the field is referenced in the format string. We pin the four
    fields the log pipeline expects (`timestamp`, `level`, `logger`,
    `message`) so every line is shaped identically — important for downstream
    label extraction.
    """


def configure_json_logging(level: str = "INFO") -> None:
    """Install a JSON formatter on the root logger and werkzeug logger.

    Idempotent: subsequent calls are no-ops so importing modules don't double-
    install handlers when entry-point scripts share initialization paths.

    Args:
        level: Root log level (string name, e.g. ``"INFO"``). Werkzeug's logger
            inherits via the root unless overridden separately.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        _StableJsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
            },
        )
    )

    root = logging.getLogger()
    # Drop any handlers a previous basicConfig call installed so plain-text
    # lines don't continue leaking to stdout alongside the JSON ones.
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Werkzeug's request handler emits its access-log lines via the
    # `werkzeug` logger using ``logger.info(format, *args)``. By the time
    # JsonFormatter sees the record the message is already formatted, so we
    # do NOT need a custom handler subclass — attaching the same JSON handler
    # is enough to wrap every access-log line in the canonical envelope.
    werkzeug = logging.getLogger("werkzeug")
    for existing in list(werkzeug.handlers):
        werkzeug.removeHandler(existing)
    werkzeug.addHandler(handler)
    # Stop the record from also being processed by the root logger's handler
    # (it already IS the root handler — propagation would double-emit).
    werkzeug.propagate = False
    werkzeug.setLevel(level.upper())

    _CONFIGURED = True
