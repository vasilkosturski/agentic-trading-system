# CI Cycle Report — 2026-07-16T07:49:39Z

## Cycle Summary

Latest cycle in the DB: runs **1101–1104**, started 2026-07-16 06:39:48 UTC. This
is a new cycle since the previous report (`CI_CYCLE_REPORT_20260714T072659Z.md`,
which covered runs 1081–1084). All 4 agent runs COMPLETED, no errors.

| Run | Agent | Decision | Symbol | Qty | Status |
|---|---|---|---|---|---|
| 1101 | Ray (Agent 3) | HOLD | — | — | COMPLETED |
| 1102 | George (Agent 2) | BUY | MU | 7 | COMPLETED |
| 1103 | Ray (Agent 3) | SELL | CRSP | 123 | COMPLETED |
| 1104 | Warren (Agent 1) | HOLD | — | — | COMPLETED |

## Phase Completeness

All 4 runs have research and decision phases recorded, with Research Context /
Portfolio Context / Historical Context all present in every decision phase.
Execution phases are recorded for the 2 BUY/SELL runs (1102, 1103); runs 1101 and
1104 (HOLD) have no execution phase, which is the expected/normal pattern for HOLD
decisions. The run-detail pages correctly show a "Phase not completed" placeholder
for HOLD runs' Execution section rather than an error.

| Run | Research tool calls | Research turns | Decision turns | Guardrail outcome | Reasoning contexts present | Execution phase |
|---|---|---|---|---|---|---|
| 1101 | 7 | 8 | 1 | first_try | all present | not applicable (HOLD) |
| 1102 | 9 | 10 | 2 | first_try | all present | COMPLETED |
| 1103 | 8 | 9 | — | first_try | all present | COMPLETED |
| 1104 | 6 | 7 | — | first_try | all present | not applicable (HOLD) |

## Portfolio Snapshots (latest per agent)

| Agent | Total Value | Cash | Holdings | Total P&L | Return % |
|---|---|---|---|---|---|
| 1 (Warren) | $108,328.78 | $33,682.60 | $74,646.18 | +$8,328.78 | +8.33% |
| 2 (George) | $98,960.51 | $26,165.97 | $72,794.54 | -$1,039.49 | -1.04% |
| 3 (Ray) | $97,643.44 | $36,117.04 | $61,526.40 | -$2,356.56 | -2.36% |
| 4 (Cathie) | $128,404.73 | $25,281.98 | $103,122.75 | +$28,404.73 | +28.40% |

## Frontend Check (Playwright)

Base URL: `https://staging.agentic-trading.vkontech.com`

- Dashboard (`/`) — loaded, 0 console messages. Agent Performance tiles and
  Portfolio Performance chart show current, correct portfolio values matching the
  DB snapshots above. **However, the run history table on the dashboard, and its
  backing `GET /api/runs?page=0&limit=20` endpoint, are stale**: the newest run
  returned is `runId:1036` (started 2026-07-09), with `"total":1036`. None of the
  latest cycle's runs (1101–1104, started 2026-07-16) appear anywhere in this list
  or in `total`, even though the DB and the per-run and portfolio-snapshot
  endpoints are fully up to date. Confirmed independently with a direct `curl`
  outside the browser and by inspecting response headers, which show
  `cache-control: no-cache, no-store, max-age=0, must-revalidate` — so this is not
  a browser/CDN cache artifact, the API itself is serving stale/capped data.
- `/runs/1101` (Ray, HOLD) — Research / Decision sections rendered with full data
  (candidates, notes, sources, tool calls, Research/Portfolio/Historical context);
  Execution section correctly shows "Phase not completed" placeholder. 0 console
  messages. Reached directly by URL — this run is not reachable via the dashboard's
  run list due to the staleness above. `GET /api/runs/1101` and `/api/agents`
  returned 200 with correct, fresh data.
- `/runs/1102` (George, BUY MU) — Research / Decision / Execution sections all
  rendered with full data, including the completed trade (7 shares MU @ $904.28,
  trade ID 874). 0 console messages. `GET /api/runs/1102` and `/api/agents`
  returned 200 with correct, fresh data.

Screenshots saved to `reports/ci-cycles/screenshots/` (CI artifact, not committed).

## Drift Comparison vs Previous Report (`CI_CYCLE_REPORT_20260714T072659Z.md`)

| Axis | Result |
|---|---|
| Completion rate | OK — 4/4 both times |
| Trades executed | Note — 2 trades this cycle (2 HOLD) vs 3 trades previous cycle (1 HOLD); within normal decision variance, no failed executions |
| Failed runs | OK — 0 both times |
| Research depth | OK — 6/7/8/9 tool calls this cycle vs 6/8/8/10 previous; within normal range |
| Reasoning completeness | OK — all contexts present both times |
| Data completeness (DB) | OK — all phases recorded per decision type both times (HOLD runs never have an execution phase, by design) |
| Frontend run-list freshness | **REGRESSION** — `/api/runs` (and the dashboard's run table) has not advanced past `runId:1036` (2026-07-09), a full week behind the actual latest run (1104, 2026-07-16), despite individual run-detail and portfolio-snapshot endpoints being fresh. Not checked at this granularity in the previous report, but this is a genuine, reproducible data-freshness bug in the run-listing API, not a comparison artifact. |

## Verdict

**FAIL** — DB-level checks (completion, phases, reasoning, portfolio snapshots) and
individual run-detail pages are all healthy for the new cycle (runs 1101–1104).
However, the dashboard's run-history list and its backing `/api/runs` endpoint are
stuck a week behind (capped at run 1036 / 2026-07-09), so the latest cycle's runs
are undiscoverable through the primary UI even though they are fully valid and
reachable by direct URL. This is a concrete, reproducible regression in the
run-listing API and blocks the gate.
