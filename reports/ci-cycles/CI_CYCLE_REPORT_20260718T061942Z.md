# CI Cycle Report — 2026-07-18T06:19:42Z

## Cycle Summary

Latest cycle in the DB: runs **1121–1124**, started 2026-07-18 00:05:03 UTC.

| Run | Agent | Decision | Symbol | Qty | Status |
|---|---|---|---|---|---|
| 1121 | Agent 1 | BUY | KO | 77 | COMPLETED |
| 1122 | Agent 2 | BUY | MOS | 298 | COMPLETED |
| 1123 | Agent 3 | SELL | CRSP | 130 | COMPLETED |
| 1124 | Agent 4 | HOLD | — | — | COMPLETED |

## Phase Completeness

All 4 runs have research and decision phases recorded, with Research Context /
Portfolio Context / Historical Context all present in every decision phase.
Execution phases are recorded for the 3 BUY/SELL runs (1121, 1122, 1123); run
1124 (HOLD) has no execution phase — expected/normal for HOLD decisions.

| Run | Research tool calls | Decision turns | Guardrail outcome | Reasoning contexts present | Execution phase |
|---|---|---|---|---|---|
| 1121 | 6 | 2 | first_try | all present | COMPLETED (trade 884) |
| 1122 | 7 | 2 | first_try | all present | COMPLETED (trade 886) |
| 1123 | 11 | 2 | first_try | all present | COMPLETED (trade 885) |
| 1124 | 7 | 1 | first_try | all present | not applicable (HOLD) |

## Portfolio Snapshots (latest per agent)

| Agent | Total Value | Cash | Holdings | Total P&L | Return % |
|---|---|---|---|---|---|
| 1 | $109,293.80 | $33,682.60 | $75,611.21 | +$9,293.80 | +9.29% |
| 2 | $97,225.32 | $26,425.74 | $70,799.58 | -$2,774.68 | -2.77% |
| 3 | $99,266.23 | $35,893.28 | $63,372.95 | -$733.77 | -0.73% |
| 4 | $118,770.51 | $25,233.33 | $93,537.18 | +$18,770.51 | +18.77% |

## Frontend Check (Playwright)

Base URL: `https://staging.agentic-trading.vkontech.com`

- Dashboard (`/`) — loaded, 0 console messages, `/api/runs`, `/api/agents`,
  `/api/portfolio/snapshots` all 200.
- `/runs/1121` (BUY KO) — Research / Decision / Execution sections all rendered
  with full data, including the completed trade (77 shares KO @ $81.56, trade
  ID 884, matches DB). 0 console messages, all API calls 200.
- `/runs/1124` (HOLD) — Research / Decision sections rendered with full data
  (candidates MCD/KO/GILD, notes, sources, tool calls, all three reasoning
  contexts). Execution section correctly shows "Phase not completed"
  placeholder. 0 console messages, all API calls 200.
- `GET /api/runs?page=0&limit=20` — newest entry is `runId:1056` (started
  2026-07-11T01:56), `total:1056`. This is exactly 7 days before the current
  date (2026-07-18), matching the documented `trading.public.display-delay-days=7`
  policy — the public list intentionally withholds runs newer than 7 days.
  Expected behavior, not a data-freshness bug: the DB and per-run endpoints are
  confirmed fresh through runs 1121–1124 above.

Screenshots saved to `reports/ci-cycles/screenshots/` (CI artifact, not committed).

## Drift Comparison vs Previous Report (`CI_CYCLE_REPORT_20260716T080500Z.md`)

| Axis | Result |
|---|---|
| Completion rate | OK — 4/4 both times |
| Trades executed | OK — 3 trades, 1 HOLD this cycle vs 2 trades, 2 HOLD previously; within normal variation |
| Failed runs | OK — 0 both times |
| Research depth | OK — 6/7/7/11 tool calls this cycle vs 6/7/8/9 previously; same range |
| Reasoning completeness | OK — all contexts present both times |
| Data completeness (DB) | OK — all phases recorded per decision type both times |
| Public run-list display delay | OK — capped at run 1056 (7 days old), consistent with the documented 7-day display-delay policy. Not a regression. |

## Verdict

**PASS** — DB-level checks (completion, phases, reasoning, portfolio snapshots),
individual run-detail pages, and the dashboard are all healthy for cycle
1121–1124. The public `/api/runs` list correctly withholds the newest runs per
the 7-day display-delay policy; this is expected behavior, not a regression.
