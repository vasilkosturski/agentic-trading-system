"""Agents SDK trace export, reconciled with the gateway cut-over.

``agents.trace(...)`` spans are shipped to ``api.openai.com/v1/traces/ingest``
authenticated with ``OPENAI_API_KEY``. The gateway does not proxy that endpoint,
and after the cut-over the agent pod holds only a virtual key — so the exporter
would log "OPENAI_API_KEY is not set, skipping trace export" once per export
batch, forever.

Three outcomes:

* ``OPENAI_TRACING_API_KEY`` set — tracing stays on, using a key scoped to trace
  ingest only. No provider key returns to the LLM call path.
* ``OPENAI_API_KEY`` set — local dev, where the provider key is present anyway.
  Unreachable in-cluster: the agent manifests deliberately never set it.
* neither key set — tracing is turned off explicitly, so the absence is a single
  startup log line instead of recurring exporter warnings.
"""

import logging

from agents import set_tracing_disabled, set_tracing_export_api_key

from config import config

logger = logging.getLogger(__name__)


def configure_tracing() -> bool:
    """Enable or disable SDK trace export based on available credentials.

    Returns True when tracing is left on.
    """
    if config.OPENAI_TRACING_API_KEY:
        set_tracing_export_api_key(config.OPENAI_TRACING_API_KEY)
        logger.info("SDK tracing enabled via OPENAI_TRACING_API_KEY")
        return True

    if config.OPENAI_API_KEY:
        logger.info("SDK tracing enabled via OPENAI_API_KEY")
        return True

    set_tracing_disabled(True)
    logger.info(
        "SDK tracing disabled: no OPENAI_API_KEY or OPENAI_TRACING_API_KEY. The "
        "gateway does not proxy /v1/traces/ingest; set OPENAI_TRACING_API_KEY to "
        "keep tracing after the gateway cut-over."
    )
    return False
