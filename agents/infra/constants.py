"""Shared sizing constants for the agents pod.

Centralizes truncation budgets that are referenced from multiple modules so
new call sites pick up the same limits without re-declaring the value.
"""

# Max characters retained from a failure's ``str(error)`` when persisted to
# the backend. Long stack traces are interesting but the backend column is
# narrow; this clamp keeps the most actionable prefix.
MAX_ERROR_MESSAGE_LEN = 500

# Max characters retained when persisting model-generated reasoning fields
# (rationale, portfolioContext, historicalContext, researchContext) on a
# completed run. The fields are intentionally short snapshots, not full
# transcripts.
MAX_REASONING_FIELD_LEN = 2000
