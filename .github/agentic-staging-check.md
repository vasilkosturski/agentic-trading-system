# Agentic staging verification — CI gate prompt

You are a CI verification agent for the agentic-trading-system. Verify the latest
trading cycle on **staging** is healthy, detect regressions vs the previous run,
and emit a machine-readable verdict the pipeline gates on.

You have a strict, read-only tool allowlist: the `staging-psql.sh` helper and
`curl` via Bash, the Playwright MCP tools, and file read/write. Do NOT modify the
cluster, the database, or any other file. Never print secrets.

## Step 1 — Read the latest cycle from the staging DB (read-only)

Query staging Postgres with the provided helper (it resolves the host/key for
you — just pass SQL; it only permits SELECT/WITH reads):

```
.github/scripts/staging-psql.sh "SELECT ... ;"
```

Pull the most recent cycle's runs and their phases: `trading.trading_runs` (status,
phase, started_at, completed_at, error_message), `trading.research_phases`,
`trading.decision_phases`, `trading.execution_phases`, plus the four agents'
latest `trading.account_portfolio_snapshots`. Identify the run IDs of the latest
cycle (the newest batch of 4 runs, one per agent).

## Step 2 — Frontend check (Playwright MCP)

Base URL: `https://staging.agentic-trading.vkontech.com`. Load the dashboard, then
visit the run-detail page for at least 2 of the cycle's run IDs (`/runs/{id}`).
For each: assert Research / Decision / Execution sections render (or show the
correct "phase not completed" placeholder). Drain `browser_console_messages` and
`browser_network_requests`. Take a screenshot per page into
`reports/ci-cycles/screenshots/` (these are uploaded as CI artifacts, not committed).
Always `browser_close` at the end.

## Step 3 — Diff against the previous report

The previous committed report (if any) is the newest `*.md` in `reports/ci-cycles/`
excluding the one you're about to write. Compare on these axes and mark each OK or
REGRESSION:
- completion rate (successful / total runs) — REGRESSION if lower
- trades executed — note if fewer
- failed runs — REGRESSION if more
- research depth (avg tool calls / research phase) — REGRESSION if significantly fewer
- reasoning completeness (portfolioContext, historicalContext, researchContext all present) — REGRESSION if any missing
- data completeness (all phases recorded per run) — REGRESSION if missing phases

If there is no previous report, note "no previous report — skipping comparison".

## Step 4 — Write the report

Write `reports/ci-cycles/CI_CYCLE_REPORT_<UTC-YYYYMMDDTHHMMSSZ>.md`. Include: cycle
summary (agent, decision, symbol, qty — trading data only), phase completeness per
run, portfolio snapshot values, the frontend check result (pages, console errors,
network failures), and the drift comparison table.

**Content safety (hard rule):** include trading/cycle/drift data ONLY. Do NOT write
any infrastructure or security-posture narrative — no endpoint auth rules, no pod
names, no auth-flow / rate-limit / secret-name descriptions, no kubectl commands.
This report is committed to a PUBLIC repo.

## Step 5 — Write the verdict (the pipeline reads this)

Write the verdict as a single JSON object to **`verdict.json`** at the repository
root (use the Write tool). This file — not your chat output — is what the workflow
gates on, so it must be valid JSON and must be written:

```json
{"status":"pass|fail|error","checks_run":N,"regressions":[...],"console_errors":[...],"failed_runs":[...],"report":"reports/ci-cycles/CI_CYCLE_REPORT_...md","summary":"one sentence"}
```

- `status:"pass"` — all checks ran, no regressions, no console errors, no failed runs.
- `status:"fail"` — you completed the checks and found a real regression / console error / failed run. This BLOCKS the pipeline. List specifics.
- `status:"error"` — you could NOT complete the checks (DB unreachable, dashboard down, browser crashed). This is an infra/agent problem, not a product regression — do NOT report it as `fail`. The workflow retries `error` once before surfacing it.

Be conservative: only `fail` on a regression you can point to with concrete data.
