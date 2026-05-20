# Vendored Model Pricing (`model_prices.json`)

This directory vendors a copy of LiteLLM's
[`model_prices_and_context_window.json`](https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json),
the de-facto community-maintained source of per-model API pricing for OpenAI,
Anthropic, Google, Bedrock, and others. It is loaded at module import time by
`agent_executor._load_model_pricing()` into the `MODEL_PRICING` table.

## Why vendor it?

- OpenAI does not expose pricing via API
  (see [openai/openai-python#2074](https://github.com/openai/openai-python/issues/2074)).
- LiteLLM keeps an exhaustive, community-curated JSON of per-model rates.
- Vendoring lets us keep the runtime offline-friendly and pricing changes
  visible as diffs in PR review (no surprise live network fetches).

## File format

Standard JSON (no comments allowed). Each entry is keyed by model name with
`input_cost_per_token` / `output_cost_per_token` as **USD per single token**.
The loader multiplies by 1,000,000 to match this module's per-1M convention.

The first entry is typically a `"sample_spec"` placeholder describing the
schema — the loader skips any entry without both cost fields.

## How to refresh

**Last refreshed: 2026-05-13.**

```bash
curl -sL https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json \
    -o agentic-trading-system/agents/infra/model_prices.json
```

Then update the date above, commit, and open a PR. The diff itself is the
audit trail of what changed in upstream LiteLLM since the previous refresh.

## Scheduled refresh

A monthly bot-PR opens automatically via
[`.github/workflows/refresh-model-prices.yml`](../.github/workflows/refresh-model-prices.yml)
on the 1st of each month at 09:00 UTC. If `agents/infra/model_prices.json` has
drifted from upstream, the workflow opens a PR titled
`chore: refresh model_prices.json from LiteLLM`.

To trigger an ad-hoc refresh between scheduled runs (from the
`agentic-trading-system` directory):

```bash
gh workflow run refresh-model-prices.yml
```

**Pricing changes are never auto-merged.** The bot opens the PR; a human
reviews and merges. Reviewer expectations:

- Glance over the diff for any obviously broken entries.
- For any flagship model whose `input_cost_per_token` or
  `output_cost_per_token` moved, sanity-check the new rate against
  <https://openai.com/api/pricing/>.
- Merge.

The manual `curl` instructions above remain useful for emergencies (Action
broken, faster-than-monthly refresh needed, air-gapped environment).
