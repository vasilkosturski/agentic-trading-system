#!/usr/bin/env bash
# Read-only staging Postgres query helper for the agentic staging check.
# The verification agent calls: staging-psql.sh "<SQL>"
# Host + key are resolved here (from the workflow env), so the agent never has
# to interpolate secrets into a command — it just passes SQL.
#
# Guardrail: reject anything that isn't a plain read. This is a read-only gate.
set -euo pipefail

SQL="${1:?usage: staging-psql.sh \"<SQL>\"}"

# Allow only SELECT/WITH read queries; block writes/DDL outright.
case "$(printf '%s' "$SQL" | tr '[:lower:]' '[:upper:]' | sed -E 's/^[[:space:]]+//')" in
  SELECT*|WITH*) ;;
  *) echo "staging-psql: refused — only SELECT/WITH read queries are allowed" >&2; exit 2 ;;
esac
case "$(printf '%s' "$SQL" | tr '[:lower:]' '[:upper:]')" in
  *INSERT*|*UPDATE*|*DELETE*|*DROP*|*ALTER*|*TRUNCATE*|*CREATE*|*GRANT*|*COPY*)
    echo "staging-psql: refused — write/DDL keyword detected" >&2; exit 2 ;;
esac

exec ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=20 \
  "root@${HETZNER_HOST}" \
  "kubectl exec postgres-0 -n agentic-trading-staging -- psql -U trading_user -d agentic_trading_staging -t -A -c \"${SQL//\"/\\\"}\""
