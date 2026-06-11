"""Tests for ``phases/research_phase.run_research_phase``.

Locks in the contract that when the guardrail-retry loop exhausts and the
helper attaches a ``GuardrailOutcome`` to the re-raised tripwire, the
phase boundary catch forwards the outcome to ``lifecycle.record_phase_failure``
and re-raises so the orchestrator's FAILED-run pathway still runs.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agents.exceptions import OutputGuardrailTripwireTriggered

# Import agent_executor first to break the circular import between
# agent_executor and phases.research_phase (agent_executor imports the phase,
# the phase imports constants from agent_executor).
import agent_executor  # noqa: F401
from ai_agents.guardrail_retry import GuardrailOutcome
from backend.run_lifecycle import RunLifecycle
from models.investment_style import InvestmentStyle
from models.orchestration import RunContext
from phases.research_phase import run_research_phase


def _make_run_context() -> RunContext:
    return RunContext(
        run_id=42,
        agent_id=1,
        agent_name="Warren",
        agent_style=InvestmentStyle.VALUE,
        model_name="gpt-4o-mini",
        research_start_time=datetime.now(),
        balance=100000.0,
        holdings=[],
        recent_activity=None,
    )


def _make_tripwire(guardrail_outcome: GuardrailOutcome | None) -> OutputGuardrailTripwireTriggered:
    """Build a tripwire exception, optionally with ``.guardrail_outcome`` pre-attached."""
    exc = OutputGuardrailTripwireTriggered.__new__(OutputGuardrailTripwireTriggered)
    exc.guardrail_result = MagicMock()
    exc.run_data = MagicMock()
    if guardrail_outcome is not None:
        exc.guardrail_outcome = guardrail_outcome  # type: ignore[attr-defined]
    return exc


@pytest.mark.asyncio
@patch("phases.research_phase.MarketAnalyst")
@patch("phases.research_phase.run_with_guardrail_retry", new_callable=AsyncMock)
async def test_research_phase_exhausted_outcome_forwards_to_lifecycle_and_reraises(
    mock_run_with_guardrail_retry: AsyncMock,
    mock_market_analyst_cls: MagicMock,
) -> None:
    """When retry exhausts with ``.guardrail_outcome`` attached, the phase catch
    must call ``lifecycle.record_phase_failure(run_id, "RESEARCH", outcome)``
    exactly once and re-raise the original tripwire."""
    # Stub the MarketAnalyst factory so the phase never touches a real agent.
    mock_agent_instance = MagicMock()
    mock_agent_instance.agent.instructions = "system prompt"
    mock_agent_instance.build_prompt.return_value = "task prompt"
    mock_market_analyst_cls.create = AsyncMock(return_value=mock_agent_instance)

    # The helper attaches ``.guardrail_outcome`` then re-raises. Reproduce that
    # contract by raising a tripwire with the outcome already attached.
    outcome = GuardrailOutcome(
        result=None,
        attempts_used=3,
        outcome="exhausted",
        last_issues=["fake_url"],
        failed_output={"summary": "bad"},
    )
    mock_run_with_guardrail_retry.side_effect = _make_tripwire(outcome)

    mock_lifecycle = MagicMock(spec=RunLifecycle)
    mock_lifecycle.record_phase_failure = AsyncMock()

    ctx = _make_run_context()

    with pytest.raises(OutputGuardrailTripwireTriggered):
        await run_research_phase(ctx=ctx, mcp_pool=MagicMock(), lifecycle=mock_lifecycle)

    mock_lifecycle.record_phase_failure.assert_awaited_once_with(42, "RESEARCH", outcome)


@pytest.mark.asyncio
@patch("phases.research_phase.MarketAnalyst")
@patch("phases.research_phase.run_with_guardrail_retry", new_callable=AsyncMock)
async def test_research_phase_tripwire_without_outcome_skips_lifecycle_and_reraises(
    mock_run_with_guardrail_retry: AsyncMock,
    mock_market_analyst_cls: MagicMock,
) -> None:
    """A tripwire without ``.guardrail_outcome`` (defensive path) must skip the
    lifecycle call but still re-raise so the FAILED pathway runs."""
    mock_agent_instance = MagicMock()
    mock_agent_instance.agent.instructions = "system prompt"
    mock_agent_instance.build_prompt.return_value = "task prompt"
    mock_market_analyst_cls.create = AsyncMock(return_value=mock_agent_instance)

    mock_run_with_guardrail_retry.side_effect = _make_tripwire(guardrail_outcome=None)

    mock_lifecycle = MagicMock(spec=RunLifecycle)
    mock_lifecycle.record_phase_failure = AsyncMock()

    ctx = _make_run_context()

    with pytest.raises(OutputGuardrailTripwireTriggered):
        await run_research_phase(ctx=ctx, mcp_pool=MagicMock(), lifecycle=mock_lifecycle)

    mock_lifecycle.record_phase_failure.assert_not_called()
