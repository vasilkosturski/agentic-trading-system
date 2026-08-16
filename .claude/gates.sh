#!/usr/bin/env bash
# This repo's pre-completion checks. Run by the parent dispatcher
# (.claude/hooks/dispatch-gates.sh at the workspace root) with cwd = repo root and
# the turn's changed paths, repo-relative, on stdin. Exit non-zero to keep the turn
# alive with the output as the reason.
#
# Mirrors CI minus what needs Docker or a network: e2e, hadolint, image builds.
# Measured warm: agents ~7s, backend ~33s (gradle), frontend a few seconds each step.
# Only the sides this turn touched run, so a one-side edit does not pay for all three.

set -uo pipefail

changed=$(cat)
touched() { printf '%s\n' "$changed" | grep -q "^$1/"; }

fail=""
run() { # run <label> <dir> <cmd...>
  local label=$1 dir=$2 out
  shift 2
  # A missing tool must fail, not be skipped: a gate that cannot run is
  # indistinguishable from one that passes.
  if ! out=$(cd "$dir" && "$@" 2>&1); then
    fail+="--- $label ---
$(printf '%s' "${out:-(no output)}" | tail -40)

"
  fi
}

if touched agents; then
  run "ruff check" agents ruff check .
  run "ruff format --check" agents ruff format --check .
  run "mypy" agents mypy ai_agents api backend infra mcp_helpers models phase_runner \
    tools utils agent_registry.py config.py logging_config.py trading_system.py
  run "pytest (unit only)" agents env RUN_EVERY_N_MINUTES=60 \
    pytest --ignore=tests/e2e -m "not integration and not e2e" -q
fi

if touched backend; then
  run "spotless + checkstyle" backend ./gradlew --no-daemon \
    spotlessCheck checkstyleMain checkstyleTest
  run "gradle test" backend ./gradlew --no-daemon test
fi

if touched frontend; then
  run "eslint" frontend npm run --silent lint
  run "tsc --noEmit" frontend npx tsc --noEmit
  run "vitest" frontend npm run --silent test -- --run
  run "build" frontend npm run --silent build
fi

[ -z "$fail" ] && exit 0
printf '%s' "$fail" >&2
exit 1
