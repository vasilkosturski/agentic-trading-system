"""End-to-end integration test for the guardrail-retry recovered path.

Forces a tripwire on attempt 1 and a clean response on attempt 2 by mocking
``Runner.run`` at the symbol the retry helper imported (``ai_agents.guardrail_retry.Runner``),
then runs the full ``run_research_phase`` pipeline with a stubbed lifecycle.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import tenacity
from agents import Usage
from agents.exceptions import OutputGuardrailTripwireTriggered

import agent_executor  # noqa: F401  -- break circular import with phases.research_phase
from ai_agents import guardrail_retry
from backend.run_lifecycle import RunLifecycle
from models.investment_style import InvestmentStyle
from models.llm_output import CandidateStock, ResearchResponse, WebSource
from models.orchestration import RunContext
from phases.research_phase import run_research_phase


@pytest.fixture(autouse=True)
def _no_retry_sleep(monkeypatch):
    monkeypatch.setattr(guardrail_retry, "_WAIT", tenacity.wait_none())


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


def _make_tripwire(rejected_payload: dict, issues: list[str]) -> OutputGuardrailTripwireTriggered:
    msg_item = MagicMock()
    msg_item.type = "message_output_item"
    msg_item._failed_output_text = json.dumps(rejected_payload)

    run_data = MagicMock()
    run_data.input = "task prompt"
    run_data.new_items = [msg_item]

    output = MagicMock()
    output.output_info = {"issues": issues}
    guardrail_result = MagicMock()
    guardrail_result.output = output

    exc = OutputGuardrailTripwireTriggered.__new__(OutputGuardrailTripwireTriggered)
    exc.guardrail_result = guardrail_result
    exc.run_data = run_data
    return exc


def _make_clean_run_result(response: ResearchResponse) -> MagicMock:
    result = MagicMock()
    result.final_output_as = MagicMock(return_value=response)
    result.new_items = []
    # Real ``extract_run_telemetry`` reads ``result.context_wrapper.usage``;
    # a zero-token ``Usage()`` is enough to exercise the helper without
    # asserting on the resulting UsageMetrics shape (that's covered by
    # telemetry's own unit tests).
    result.context_wrapper.usage = Usage()
    return result


@pytest.mark.asyncio
@patch("phases.research_phase.MarketAnalyst")
@patch("ai_agents.guardrail_retry.Runner")
async def test_research_phase_recovered_path_populates_guardrail_fields(
    mock_runner_cls,
    mock_market_analyst_cls,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        guardrail_retry,
        "_message_output_text",
        lambda item: getattr(item, "_failed_output_text", ""),
    )

    mock_agent_instance = MagicMock()
    mock_agent_instance.agent.instructions = "system prompt"
    mock_agent_instance.build_prompt.return_value = "task prompt"
    mock_agent_instance.model_name = "gpt-4o-mini"
    mock_market_analyst_cls.create = AsyncMock(return_value=mock_agent_instance)

    rejected_payload = {
        "summary": "Banks look hot.",
        "candidates": [{"symbol": "FAKE", "price": -1}],
        "webSources": [{"title": "n/a", "url": "http://example.invalid"}],
    }
    issues = ["fake_url", "empty_candidates"]
    tripwire = _make_tripwire(rejected_payload, issues)

    clean_response = ResearchResponse(
        summary="Banks show strong fundamentals.",
        candidates=[CandidateStock(symbol="JPM", price=195.50)],
        webSources=[WebSource(title="WSJ Banks Report", url="https://example.com/wsj")],
    )
    clean_result = _make_clean_run_result(clean_response)

    mock_runner_cls.run = AsyncMock(side_effect=[tripwire, clean_result])

    mock_lifecycle = MagicMock(spec=RunLifecycle)
    mock_lifecycle.record_phase_failure = AsyncMock()

    ctx = _make_run_context()

    research_result = await run_research_phase(
        ctx=ctx, mcp_pool=MagicMock(), lifecycle=mock_lifecycle
    )

    assert mock_runner_cls.run.await_count == 2
    assert research_result.guardrail_outcome == "recovered"
    assert research_result.guardrail_attempts == 2
    assert research_result.guardrail_issues == issues
    assert research_result.guardrail_failed_output == rejected_payload
    mock_lifecycle.record_phase_failure.assert_not_called()
