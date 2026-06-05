"""Centralized JSON logging configuration for the agents service.

Log shippers (Grafana Alloy, Promtail, Fluent Bit) extract structured fields
from a JSON envelope; the Loki ``level`` label is read from an explicit field
rather than inferred from substring matches on free-form text. Each emitted
line is a single-line JSON object with ``timestamp``, ``level``, ``logger``,
``message``. Werkzeug's access-log logger is reattached to the same JSON
formatter so its lines flow through the same envelope.
"""

from __future__ import annotations

import logging
import sys

from pythonjsonlogger.json import JsonFormatter

_CONFIGURED = False


class _StableJsonFormatter(JsonFormatter):
    """JsonFormatter that always emits the canonical key set.

    The base class only writes a field if either the record has a non-empty
    value OR the field is referenced in the format string. Pinning the four
    fields ``timestamp``/``level``/``logger``/``message`` keeps every line
    shaped identically for downstream label extraction.
    """


def configure_json_logging(level: str = "INFO") -> None:
    """Install a JSON formatter on the root and werkzeug loggers.

    Idempotent: subsequent calls are no-ops so importing modules don't double-
    install handlers when entry-point scripts share initialization paths.
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
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level.upper())

    werkzeug = logging.getLogger("werkzeug")
    for existing in list(werkzeug.handlers):
        werkzeug.removeHandler(existing)
    werkzeug.addHandler(handler)
    # propagate=False stops werkzeug records from reaching the root handler
    # (which already IS the root handler — propagation would double-emit).
    werkzeug.propagate = False
    werkzeug.setLevel(level.upper())

    _CONFIGURED = True
