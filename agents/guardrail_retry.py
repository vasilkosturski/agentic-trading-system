"""Reusable guardrail retry loop for OpenAI Agents SDK.

Extracts the retry-on-guardrail-rejection pattern into a standalone async
function so it can be tested independently and reused across agents.
"""

import logging
from typing import Any

from agents import Agent, ItemHelpers, Runner
from agents.exceptions import OutputGuardrailTripwireTriggered
from agents.result import RunResult

logger = logging.getLogger(__name__)


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
    an error feedback message so the LLM can self-correct, and retries.

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

    for attempt in range(1, max_attempts + 1):
        try:
            result = await Runner.run(agent, input_for_run, max_turns=max_turns)
            return result
        except OutputGuardrailTripwireTriggered as e:
            if attempt == max_attempts:
                logger.error(
                    "Output guardrail failed after %d attempts for %s",
                    max_attempts,
                    agent_name,
                )
                raise

            error_info = e.guardrail_result.output.output_info
            logger.warning(
                "Output rejected (attempt %d/%d) for %s: %s",
                attempt,
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
            input_items.append({
                "role": "user",
                "content": (
                    f"Output validation failed, fix your response: {error_info}"
                ),
            })
            input_for_run = input_items

    # Unreachable: the loop always returns or raises, but satisfy the type checker.
    raise RuntimeError("run_with_guardrail_retry: unexpected exit from retry loop")
