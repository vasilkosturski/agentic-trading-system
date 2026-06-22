"""End-to-end integration test for the guardrail-retry recovered path.

Forces a tripwire on attempt 1 and a clean response on attempt 2 by mocking
``Runner.run`` at the symbol the retry helper imported
(``ai_agents.guardrail_retry.Runner``), then runs the full ``run_cycle``
pipeline with a stubbed BackendClient.

Asserts the recovered metrics propagate all the way to ``complete_run``'s
payload — the public contract a downstream observer would see.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import tenacity
from agents import Usage
from agents.exceptions import OutputGuardrailTripwireTriggered

from ai_agents import guardrail_retry
from models.api_responses import AccountReport, RecentActivityResponse
from models.investment_style import InvestmentStyle
from models.llm_output import (
    CandidateStock,
    ResearchResponse,
    TradeAction,
    TradingDecision,
    WebSource,
)


@pytest.fixture(autouse=True)
def _no_retry_sleep(monkeypatch):
    monkeypatch.setattr(guardrail_retry, "_WAIT", tenacity.wait_none())


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


def _make_clean_run_result(final_output) -> MagicMock:
    result = MagicMock()
    result.final_output_as = MagicMock(return_value=final_output)
    result.new_items = []
    # Real ``extract_run_telemetry`` reads ``result.context_wrapper.usage``;
    # a zero-token ``Usage()`` is enough to exercise the helper without
    # asserting on the resulting UsageMetrics shape (covered by telemetry's
    # own unit tests).
    result.context_wrapper.usage = Usage()
    return result


@pytest.mark.asyncio
@patch("phase_runner.cycle.DecisionMaker")
@patch("phase_runner.cycle.MarketAnalyst")
@patch("ai_agents.guardrail_retry.Runner")
async def test_run_cycle_recovered_guardrail_persists_recovered_metrics(
    mock_runner_cls,
    mock_market_analyst_cls,
    mock_decision_maker_cls,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        guardrail_retry,
        "_message_output_text",
        lambda item: getattr(item, "_failed_output_text", ""),
    )

    # --- Market Analyst stub ---
    ma_instance = MagicMock()
    ma_instance.agent.instructions = "system prompt"
    ma_instance.build_prompt.return_value = "task prompt"
    ma_instance.model_name = "gpt-4o-mini"
    mock_market_analyst_cls.create = AsyncMock(return_value=ma_instance)

    # --- Decision Maker stub (cycle still runs it after recovery) ---
    dm_instance = MagicMock()
    dm_instance.agent.instructions = "decision system prompt"
    dm_instance.build_prompt.return_value = "decision task prompt"
    dm_instance.model_name = "gpt-4o-mini"
    mock_decision_maker_cls.create = AsyncMock(return_value=dm_instance)

    # --- Guardrail trip → recover sequence on Runner.run ---
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
    clean_research_result = _make_clean_run_result(clean_response)

    hold_decision = TradingDecision(
        action=TradeAction.HOLD,
        symbol="",
        quantity=0,
        rationale="Stay put",
        portfolioContext="balanced",
        historicalContext="quiet",
        researchContext="banks",
    )
    decision_run_result = _make_clean_run_result(hold_decision)

    # Two Runner.run calls happen via the guardrail helper (trip → recover),
    # plus a bare Runner.run from the decision phase. Three total.
    mock_runner_cls.run = AsyncMock(side_effect=[tripwire, clean_research_result])

    # --- BackendClient stub ---
    client = MagicMock()
    client.initialize_agent = AsyncMock(return_value=1)
    client.create_run = AsyncMock(return_value=42)
    client.update_phase = AsyncMock(return_value=None)
    client.complete_run = AsyncMock(return_value=None)
    client.record_phase_failure = AsyncMock(return_value=None)
    client.get_account_report = AsyncMock(
        return_value=AccountReport(
            agentName="Warren",
            balance=100000.0,
            holdingsValue=0.0,
            totalPortfolioValue=100000.0,
            initialBalance=100000.0,
            totalProfitLoss=0.0,
            profitLossPercent=0.0,
            holdingsCount=0,
            transactionCount=0,
            holdings=[],
        )
    )
    client.get_recent_activity = AsyncMock(
        return_value=RecentActivityResponse(
            agentName="Warren", days=30, runs=[], totalRuns=0, totalTrades=0
        )
    )

    with (
        patch("phase_runner.cycle.get_backend_client", return_value=client),
        patch("phase_runner._lifecycle.get_backend_client", return_value=client),
        patch("phase_runner._lifecycle.broadcast_status"),
        patch(
            "phase_runner.cycle.Runner.run",
            new=AsyncMock(return_value=decision_run_result),
        ),
    ):
        from phase_runner import run_cycle

        await run_cycle(
            agent_id=1,
            name="Warren",
            agent_style=InvestmentStyle.VALUE,
            mcp_pool=MagicMock(),
            model_name="gpt-4o-mini",
            force_trade=False,
        )

    # Guardrail helper retried (tripped → recovered).
    assert mock_runner_cls.run.await_count == 2

    # The recovered metrics propagate all the way to complete_run.
    client.complete_run.assert_awaited_once()
    complete_data = client.complete_run.await_args.args[1]
    assert complete_data.research.guardrailOutcome == "recovered"
    assert complete_data.research.guardrailAttempts == 2
    assert complete_data.research.guardrailIssues == issues
    assert complete_data.research.guardrailFailedOutput == rejected_payload

    # Recovered path means no exhaustion stub was persisted.
    client.record_phase_failure.assert_not_awaited()
