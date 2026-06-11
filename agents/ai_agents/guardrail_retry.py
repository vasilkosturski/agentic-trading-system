"""Reusable guardrail retry loop for OpenAI Agents SDK.

Extracts the retry-on-guardrail-rejection pattern into a standalone async
function so it can be tested independently and reused across agents.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from agents import Agent, ItemHelpers, Runner
from agents.exceptions import OutputGuardrailTripwireTriggered
from agents.items import MessageOutputItem
from agents.result import RunResult
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)


GuardrailOutcomeLiteral = Literal["first_try", "recovered", "exhausted"]


@dataclass
class GuardrailOutcome:
    """Per-phase summary of guardrail-retry behaviour.

    Returned by ``run_with_guardrail_retry`` instead of the bare
    ``RunResult`` so callers can persist a 1:1 outcome row on the audit
    table. ``last_issues`` is populated only when at least one attempt
    failed (i.e. ``outcome != "first_try"``). ``failed_output`` carries
    the LLM's last rejected response as a JSON-safe dict, surfacing the
    "what did the model actually produce that got flagged?" payload for
    the debug view; ``None`` on first-try success.
    """

    result: RunResult | None
    attempts_used: int
    outcome: GuardrailOutcomeLiteral
    last_issues: list[str] = field(default_factory=list)
    failed_output: dict | None = None


# Backoff between attempts: 1s, 2s, 4s, ... capped at 16s, with jitter.
# Exposed at module scope so tests can monkeypatch it to ``wait_none()`` and
# keep retry tests fast and deterministic.
_WAIT = wait_exponential_jitter(initial=1, max=16)


# Indirection so tests can patch the SDK text-extraction call without
# constructing a full ``ResponseOutputMessage``. Production path delegates
# straight to the SDK helper.
def _message_output_text(item: MessageOutputItem) -> str:
    return ItemHelpers.text_message_output(item)


def _capture_failed_output(run_data: Any) -> dict | None:
    """Pull the LLM's rejected JSON out of a tripwire's ``run_data``.

    The agent's structured output is emitted as a ``MessageOutputItem``
    whose raw text is the JSON payload that failed validation. Walk the
    items in reverse and decode the last message; fall back to a
    ``{"raw_text": ...}`` envelope when the output isn't valid JSON so the
    audit trail still records what was rejected.

    SDK contract: each retry attempt emits exactly one final
    ``MessageOutputItem`` whose text is the structured-output JSON. A
    malformed item that makes ``ItemHelpers.text_message_output`` raise
    must NOT crash the retry loop — capture failure is best-effort, so
    swallow any exception and return ``None``. The persisted audit row
    loses ``failed_output`` for that attempt, but the loop continues.
    """
    if run_data is None:
        return None
    new_items = getattr(run_data, "new_items", None) or []
    for item in reversed(new_items):
        if getattr(item, "type", None) != "message_output_item":
            continue
        try:
            text = _message_output_text(item)
        except Exception as exc:
            logger.warning(
                "guardrail_capture_failed_output_error",
                extra={
                    "event_type": "guardrail_capture_failed_output_error",
                    "error": str(exc),
                },
            )
            return None
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            return {"raw_text": text}
        if isinstance(parsed, dict):
            return parsed
        return {"value": parsed}
    return None


def _extract_issues(error_info: Any) -> list[str]:
    """Pull the ``issues`` list out of a guardrail ``output_info`` payload.

    Guardrail implementations return ``{"issues": [...]}`` from
    ``GuardrailFunctionOutput.output_info``. Older or custom guardrails may
    return a bare string or another shape; in that case we coerce to a single-
    element list so the structured field stays a ``list[str]`` for log
    indexers.
    """
    if isinstance(error_info, dict):
        issues = error_info.get("issues", [])
        if isinstance(issues, list):
            return [str(item) for item in issues]
        return [str(issues)]
    return [str(error_info)]


async def run_with_guardrail_retry(
    agent: Agent[Any],
    input: str | list,
    max_attempts: int = 3,
    max_turns: int = 30,
    agent_name: str = "",
    run_id: int | None = None,
) -> GuardrailOutcome:
    """Run an agent with automatic retry on output guardrail rejection.

    When an output guardrail rejects the agent's response, this function
    reconstructs the conversation from the exception's ``run_data``, appends
    an error feedback message so the LLM can self-correct, and retries with
    exponential backoff plus jitter between attempts.

    Args:
        agent: The Agent instance to run.
        input: Initial prompt string or input item list.
        max_attempts: Maximum number of attempts before re-raising.
        max_turns: Maximum turns per ``Runner.run`` call.
        agent_name: Human-readable agent name for log messages.
        run_id: Optional run identifier from ``RunContext``; surfaces in the
            structured log payload so Loki can correlate events to runs.

    Returns:
        A ``GuardrailOutcome`` wrapping the successful ``RunResult`` plus
        the per-phase summary (attempts used, outcome label, last failed
        issues). On exhaustion the function re-raises rather than
        returning — callers receive a ``GuardrailOutcome`` only for
        ``first_try`` or ``recovered`` paths.

    Raises:
        OutputGuardrailTripwireTriggered: If all attempts are exhausted.
    """
    input_for_run: str | list = input
    last_failed_attempt: int = 0
    last_failed_issues: list[str] = []
    last_failed_output: dict | None = None

    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=_WAIT,
        retry=retry_if_exception_type(OutputGuardrailTripwireTriggered),
        reraise=True,
    ):
        with attempt:
            try:
                result = await Runner.run(agent, input_for_run, max_turns=max_turns)
                attempts_used = attempt.retry_state.attempt_number
                # If we recovered after at least one failed attempt, emit a
                # resolved event so dashboards can count successful recoveries.
                if last_failed_attempt >= 1:
                    logger.info(
                        "guardrail_resolved",
                        extra={
                            "event_type": "guardrail_resolved",
                            "agent_name": agent_name,
                            "attempt": attempts_used,
                            "max_attempts": max_attempts,
                            "issues": last_failed_issues,
                            "run_id": run_id,
                        },
                    )
                    return GuardrailOutcome(
                        result=result,
                        attempts_used=attempts_used,
                        outcome="recovered",
                        last_issues=last_failed_issues,
                        failed_output=last_failed_output,
                    )
                return GuardrailOutcome(
                    result=result,
                    attempts_used=attempts_used,
                    outcome="first_try",
                    last_issues=[],
                    failed_output=None,
                )
            except OutputGuardrailTripwireTriggered as e:
                attempt_number = attempt.retry_state.attempt_number
                error_info = e.guardrail_result.output.output_info
                issues = _extract_issues(error_info)
                last_failed_attempt = attempt_number
                last_failed_issues = issues
                last_failed_output = _capture_failed_output(e.run_data)

                if attempt_number >= max_attempts:
                    logger.error(
                        "guardrail_exhausted",
                        extra={
                            "event_type": "guardrail_exhausted",
                            "agent_name": agent_name,
                            "attempt": attempt_number,
                            "max_attempts": max_attempts,
                            "issues": issues,
                            "run_id": run_id,
                        },
                    )
                    # Attach the exhausted outcome to the exception so
                    # callers can persist failed_output + issues + attempts
                    # alongside the re-raised tripwire without re-deriving them.
                    e.guardrail_outcome = GuardrailOutcome(  # type: ignore[attr-defined]
                        result=None,
                        attempts_used=attempt_number,
                        outcome="exhausted",
                        last_issues=issues,
                        failed_output=last_failed_output,
                    )
                else:
                    logger.warning(
                        "guardrail_tripped",
                        extra={
                            "event_type": "guardrail_tripped",
                            "agent_name": agent_name,
                            "attempt": attempt_number,
                            "max_attempts": max_attempts,
                            "issues": issues,
                            "run_id": run_id,
                        },
                    )

                # Reconstruct conversation from the exception's run_data.
                # The SDK always attaches run_data when a guardrail tripwire fires;
                # if it's missing, something is wrong upstream and we cannot
                # rebuild the conversation -- fail loudly instead of papering over.
                if e.run_data is None:
                    raise RuntimeError(
                        "OutputGuardrailTripwireTriggered raised without run_data; "
                        "cannot reconstruct conversation for retry"
                    ) from e

                input_items = ItemHelpers.input_to_new_input_list(e.run_data.input)
                for item in e.run_data.new_items:
                    if item.type == "tool_approval_item":
                        continue  # ToolApprovalItems cannot be converted
                    input_items.append(item.to_input_item())

                # Append error feedback so the LLM knows what to fix
                input_items.append(
                    {
                        "role": "user",
                        "content": (f"Output validation failed, fix your response: {error_info}"),
                    }
                )
                input_for_run = input_items
                raise

    # Unreachable: AsyncRetrying always returns from inside the loop or
    # re-raises once stop_after_attempt is exhausted. Retained for the type
    # checker, which cannot infer that the async-for body must terminate.
    raise RuntimeError("run_with_guardrail_retry: unexpected exit from retry loop")
