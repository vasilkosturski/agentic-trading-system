"""Reusable guardrail retry loop for OpenAI Agents SDK.

Extracts the retry-on-guardrail-rejection pattern into a standalone async
function so it can be tested independently and reused across agents.
"""

import logging
from typing import Any

from agents import Agent, ItemHelpers, Runner
from agents.exceptions import OutputGuardrailTripwireTriggered
from agents.result import RunResult
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)


# Backoff between attempts: 1s, 2s, 4s, ... capped at 16s, with jitter.
# Exposed at module scope so tests can monkeypatch it to ``wait_none()`` and
# keep retry tests fast and deterministic.
_WAIT = wait_exponential_jitter(initial=1, max=16)


async def run_with_guardrail_retry(
    agent: Agent[Any],
    input: str | list,
    max_attempts: int = 3,
    max_turns: int = 30,
    agent_name: str = "",
) -> RunResult:
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

    Returns:
        The successful ``RunResult``.

    Raises:
        OutputGuardrailTripwireTriggered: If all attempts are exhausted.
    """
    input_for_run: str | list = input

    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=_WAIT,
        retry=retry_if_exception_type(OutputGuardrailTripwireTriggered),
        reraise=True,
    ):
        with attempt:
            try:
                return await Runner.run(agent, input_for_run, max_turns=max_turns)
            except OutputGuardrailTripwireTriggered as e:
                attempt_number = attempt.retry_state.attempt_number
                error_info = e.guardrail_result.output.output_info

                if attempt_number >= max_attempts:
                    logger.error(
                        "Output guardrail failed after %d attempts for %s",
                        max_attempts,
                        agent_name,
                    )
                else:
                    logger.warning(
                        "Output rejected (attempt %d/%d) for %s: %s",
                        attempt_number,
                        max_attempts,
                        agent_name,
                        error_info,
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
