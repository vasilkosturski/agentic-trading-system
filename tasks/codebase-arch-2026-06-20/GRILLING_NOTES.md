# Grilling Notes — Candidate #1: Deepen the agent phase-runner chain

**Picked from:** `CANDIDATES.md` (this directory) — Candidate 1
**Approved plan:** `/Users/vkosturski/.claude/plans/shimmying-rolling-newell.md`
**Date:** 2026-06-20

## Scope of the deepening

Collapse 8 source files into one **`PhaseRunner`** Module under `agents/phase_runner/`. The Module exposes a single async entry point; everything else becomes private.

Bundled with this deepening (ride-along): Candidate #5 (delete `agents/backend/run_tracking.py` + the non-decorated forwarders in `agents/tools/trading_tools.py`) — `_lifecycle.py` calls `BackendClient` directly, making those wrappers instantly dead.

## Resolved decision tree

- **Q1 — Should `RunLifecycle` be absorbed into `PhaseRunner` or kept as a separate (private) collaborator?**
  **A:** Absorb as a private internal (`_lifecycle.py`).
  *(why: grep confirmed zero callers outside `agent_executor.execute_cycle`; keeping it public lets the "every phase transition happens inside the cycle" invariant leak. Counter — heavy test mocking of `mock_lifecycle.transition_to_*` — gets resolved by Q7's test surface rewrite.)*

- **Q2 — Should `run_cycle` return a `CycleOutcome` dataclass for testability?**
  **A:** Return `None`. Pure side-effect.
  *(why: no production caller consumes a return value today; building one "for tests" violates the test-surface principle. Tests cross the same seams production reads via — BackendClient HTTP + broadcast bus.)*

- **Q3 — Descriptor table or open-coded sequence in `run_cycle`?**
  **A:** Open-coded.
  *(why: 4 phases with subtle per-phase quirks — research has `OutputGuardrailTripwireTriggered` handling, finalization has no agent call, prompt capture differs slightly. Descriptor table grows nullable fields + `if descriptor.has_guardrail:` special cases. Open-coded narrative reads top-to-bottom; adding a 5th phase = new section, same friction as new row.)*

- **Q4 — Single file `phase_runner.py` or package `phase_runner/`?**
  **A:** Package with three files: `cycle.py` + `_lifecycle.py` + `_telemetry.py`. `__init__.py` only re-exports `run_cycle`.
  *(why: realistic post-collapse size is 500-700 LOC — too chunky for one Python file. Split is by **cohesion of leaf detail**, not by phase: phases stay together in `cycle.py` as the narrative; orthogonal concerns (lifecycle wiring, SDK telemetry) become private leaf modules at the bottom of the call graph. Reader's story stays in one file; they only drop into leaves for "how does this work?" questions, not "what happens next?")*

- **Q5 — Does `agent_executor.py` survive as a 1-line shim (`from phase_runner import run_cycle as execute_cycle`)?**
  **A:** Delete entirely.
  *(why: production has exactly 1 caller (`ai_agents/simple_trader.py:25`); updating one import beats the cognitive overhead of `execute_cycle` vs `run_cycle`. Project CLAUDE.md explicitly disallows BC shims. Deletes ~330 LOC: `agent_executor.py` (244) + `conftest._redirect_run_lifecycle_to_agent_executor` autouse fixture (~85) + 2 `noqa: F401` workaround imports.)*

- **Q6 — Migration: big-bang or stepwise?**
  **A:** Big-bang. One diff, one PR.
  *(why: stepwise creates a worse intermediate state — two ways to run a cycle, ambient confusion about which is canonical, tests for both. Deepening's value IS the locality; stepwise delivers no value until the final step, at which point it's the same risk as big-bang. Single-author project on `main` makes a red-mid-PR window acceptable.)*

- **Q7 — Test surface: keep per-phase tests or end-to-end only?**
  **A:** End-to-end only. Rewrite `test_agent_executor.py` → `test_phase_runner.py`; delete `test_research_phase.py`, `test_decision_phase.py`, `test_execution_phase.py`, `test_run_lifecycle.py`; delete `_redirect_run_lifecycle_to_agent_executor` autouse fixture. Keep `test_guardrail_e2e_integration.py` + `e2e/test_full_cycle_e2e.py` with updated mock targets.
  *(why: the Interface IS the test surface. Testing past it means the Module is the wrong shape. Per-phase coverage would force re-shallowing `phase_runner` to make internals semi-public.)*

- **Q8 — Bundle Candidate #5 (`run_tracking.py` deletion) into the same diff?**
  **A:** Bundle it.
  *(why: `_lifecycle.py` will call `BackendClient` directly via `get_backend_client()`. Once it does, `run_tracking.py`'s 2-line forwarders are instantly dead. Deferring leaves a half-finished smell.)*

## Files in scope (full list for downstream review)

**New:**
- `agents/phase_runner/__init__.py`
- `agents/phase_runner/cycle.py`
- `agents/phase_runner/_lifecycle.py`
- `agents/phase_runner/_telemetry.py`
- `agents/tests/test_phase_runner.py` (rewrite of `test_agent_executor.py`)

**Deleted:**
- `agents/agent_executor.py`
- `agents/phases/research_phase.py`
- `agents/phases/decision_phase.py`
- `agents/phases/execution_phase.py`
- `agents/phases/finalization.py`
- `agents/phases/__init__.py` (package becomes empty)
- `agents/backend/run_lifecycle.py`
- `agents/backend/run_tracking.py`
- `agents/tools/trading_tools.py` (the 6 non-decorated forwarders only; keep `function_tool`-decorated entries if any)
- `agents/tests/test_agent_executor.py`
- `agents/tests/test_research_phase.py`
- `agents/tests/test_decision_phase.py`
- `agents/tests/test_execution_phase.py`
- `agents/tests/test_run_lifecycle.py`

**Modified:**
- `agents/ai_agents/simple_trader.py` (import + call site)
- `agents/tests/conftest.py` (delete forwarder fixture; update remaining `agent_executor.*` / `run_lifecycle.*` patches to `phase_runner._lifecycle.*`)
- `agents/tests/test_guardrail_e2e_integration.py` (update mock targets)
- `agents/tests/e2e/test_full_cycle_e2e.py` (one import update)

**Unchanged but called from the new internals:**
- `agents/backend/client.py` (`BackendClient` — `_lifecycle.py` calls it directly)
- `agents/utils/sdk_parser.py` (pulled into `_telemetry.py`'s private surface)
- `agents/infra/telemetry.py` (pulled into `_telemetry.py`)
- `agents/infra/pricing.py` (data table)

## Out of scope (deliberately deferred to follow-up PRs)

- Candidate #6 — merge `sdk_parser.py` + `telemetry.py` into one `Telemetry` Module
- Candidate #7 — push `BackendClient` test seam down to `httpx.MockTransport`
- Spring Boot Candidates #2, #3 — separate Java diff
- Frontend Candidate #4 — separate React diff
