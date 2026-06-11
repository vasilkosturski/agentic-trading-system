"""Tests for ``phases/decision_phase.run_decision_phase`` exhaustion catch.

The Decision Maker doesn't go through ``run_with_guardrail_retry`` today —
the bare ``Runner.run`` path means no ``.guardrail_outcome`` attribute will
be attached to a tripwire under the current wiring. The catch is reserved
for the future retry-wired path.

These tests pin the contract so a future wiring change can't silently regress it:
* With ``.guardrail_outcome`` attached → lifecycle.record_phase_failure
  called once with ``"DECISION"`` + the outcome, then re-raise.
* Without it (defensive path) → skip lifecycle, re-raise.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agents.exceptions import OutputGuardrailTripwireTriggered

# Import agent_executor first to break the circular import between
# agent_executor and phases.decision_phase.
import agent_executor  # noqa: F401
from ai_agents.guardrail_retry import GuardrailOutcome
from backend.run_lifecycle import RunLifecycle
from models.investment_style import InvestmentStyle
from models.llm_output import ResearchResponse
from models.orchestration import ResearchResult, RunContext
from phases.decision_phase import run_decision_phase


def _make_run_context_with_research() -> RunContext:
    research_response = ResearchResponse(
        summary="Banks look strong.",
        candidates=[],
        webSources=[],
    )
    research_result = ResearchResult(
        research_response=research_response,
        candidates=[],
        sources=[],
        notes="",
    )
    ctx = RunContext(
        run_id=99,
        agent_id=1,
        agent_name="Warren",
        agent_style=InvestmentStyle.VALUE,
        model_name="gpt-4o-mini",
        research_start_time=datetime.now(),
        balance=100000.0,
        holdings=[],
        recent_activity=None,
    )
    ctx.research = research_result
    return ctx


def _make_tripwire(guardrail_outcome: GuardrailOutcome | None) -> OutputGuardrailTripwireTriggered:
    exc = OutputGuardrailTripwireTriggered.__new__(OutputGuardrailTripwireTriggered)
    exc.guardrail_result = MagicMock()
    exc.run_data = MagicMock()
    if guardrail_outcome is not None:
        exc.guardrail_outcome = guardrail_outcome  # type: ignore[attr-defined]
    return exc


@pytest.mark.asyncio
@patch("phases.decision_phase.Runner")
@patch("phases.decision_phase.DecisionMaker")
async def test_decision_phase_exhausted_outcome_forwards_to_lifecycle_and_reraises(
    mock_decision_maker_cls: MagicMock,
    mock_runner_cls: MagicMock,
) -> None:
    """Forward-compat contract: when ``Runner.run`` raises a tripwire with
    ``.guardrail_outcome`` pre-attached (the Batch B retry-helper shape),
    the phase catch must persist via lifecycle and re-raise."""
    mock_agent_instance = MagicMock()
    mock_agent_instance.agent.instructions = "system prompt"
    mock_agent_instance.build_prompt.return_value = "task prompt"
    mock_decision_maker_cls.create = AsyncMock(return_value=mock_agent_instance)

    outcome = GuardrailOutcome(
        result=None,
        attempts_used=3,
        outcome="exhausted",
        last_issues=["invalid_action"],
        failed_output={"action": "BUY"},
    )
    mock_runner_cls.run = AsyncMock(side_effect=_make_tripwire(outcome))

    mock_lifecycle = MagicMock(spec=RunLifecycle)
    mock_lifecycle.transition_to_deciding = AsyncMock()
    mock_lifecycle.record_phase_failure = AsyncMock()

    ctx = _make_run_context_with_research()

    with pytest.raises(OutputGuardrailTripwireTriggered):
        await run_decision_phase(
            ctx=ctx,
            mcp_pool=MagicMock(),
            force_trade=False,
            lifecycle=mock_lifecycle,
        )

    mock_lifecycle.record_phase_failure.assert_awaited_once_with(99, "DECISION", outcome)


@pytest.mark.asyncio
@patch("phases.decision_phase.Runner")
@patch("phases.decision_phase.DecisionMaker")
async def test_decision_phase_tripwire_without_outcome_skips_lifecycle_and_reraises(
    mock_decision_maker_cls: MagicMock,
    mock_runner_cls: MagicMock,
) -> None:
    """Today's path: ``Runner.run`` raises a bare tripwire (no
    ``.guardrail_outcome``). The catch must skip lifecycle and re-raise."""
    mock_agent_instance = MagicMock()
    mock_agent_instance.agent.instructions = "system prompt"
    mock_agent_instance.build_prompt.return_value = "task prompt"
    mock_decision_maker_cls.create = AsyncMock(return_value=mock_agent_instance)

    mock_runner_cls.run = AsyncMock(side_effect=_make_tripwire(guardrail_outcome=None))

    mock_lifecycle = MagicMock(spec=RunLifecycle)
    mock_lifecycle.transition_to_deciding = AsyncMock()
    mock_lifecycle.record_phase_failure = AsyncMock()

    ctx = _make_run_context_with_research()

    with pytest.raises(OutputGuardrailTripwireTriggered):
        await run_decision_phase(
            ctx=ctx,
            mcp_pool=MagicMock(),
            force_trade=False,
            lifecycle=mock_lifecycle,
        )

    mock_lifecycle.record_phase_failure.assert_not_called()
