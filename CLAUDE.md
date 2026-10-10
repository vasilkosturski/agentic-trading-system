# agentic-trading-system

Demo multi-agent stock trading system. Four AI traders (Warren, George, Ray, Cathie) start with $100K of virtual money each and run a Market Analyst → Decision Maker pipeline that ends in BUY, SELL or HOLD. Live at agentic-trading.vkontech.com.

This repo is public. Cluster, host and deploy details live in the private `agentic-trading-system-infra` repo; keep them out of here.

## Layout

- `agents/`: Python 3.11 on the OpenAI Agents SDK, with Brave Search and Fetch MCP. Entry point `trading_system.py`; `agents/backend/` is the HTTP client to the Java backend, not the backend itself.
- `backend/`: Java 21, Spring Boot, Gradle. Accounts, trades, the run and audit trail, and the agents' prompts in `src/main/resources/prompts/`.
- `frontend/`: React 19, Vite, Mantine dashboard.
- `reports/ci-cycles/`: trading-cycle reports committed by CI.
- `.github/agentic-staging-check.md`: prompt for the headless Claude check that runs before a prod promote.

## Commands

- Full stack: `cp .env.example .env`, fill it in, `docker compose up --build`. Dashboard on :5173, API on :8080.
- Agents, cwd `agents/`: `ruff check .`, `ruff format --check .`, mypy, `RUN_EVERY_N_MINUTES=60 pytest --ignore=tests/e2e -m "not integration and not e2e" -q`.
- Backend, cwd `backend/`: `./gradlew --no-daemon spotlessCheck checkstyleMain checkstyleTest test`.
- Frontend, cwd `frontend/`: `npm run lint`, `npx tsc --noEmit`, `npm run test -- --run`, `npm run build`.
- `.claude/gates.sh` runs only the sides a change touched.

## Release

- Push to `main` runs `main.yml`: lint and tests, images tagged `:sha-<commit>`, e2e with real OpenAI, Brave and Finnhub calls (about 7¢), staging rollout, smoke.
- Production goes through `promote-prod.yml`, dispatched by hand and only on the owner's say-so. It runs the Claude staging check, retags the image staging runs as `:prod-<sha>` and rolls prod.

## Decided on purpose

Read these before "fixing" one of them.

- The public `/api/runs` hides the last 7 days (`display-delay-days: 7` in `application.yml`). e2e sets it to 0.
- A HOLD run has no execution phase.
- Behind the LLM gateway, agents send an intent (`research-tier`, `decision-tier`) instead of a model name. Without the gateway they send no ModelSettings at all, because effort and tags make the provider return 400.
- The gateway has no cross-provider fallback and no semantic cache.
- Hibernate `ddl-auto: update` owns the schema; there is no Flyway.
- Prompts live in `backend/`, not in `agents/`.

## Traps

- `trading_system.py` raises at import time when `RUN_EVERY_N_MINUTES` is unset, so pytest needs it in the environment.
- `BACKEND_ADMIN_PASSWORD` must equal `ADMIN_PASSWORD`, otherwise login returns 400.
- Set both `LLM_GATEWAY_BASE_URL` and `LLM_GATEWAY_API_KEY`, or neither.
- The ruff version in `.pre-commit-config.yaml` must match `pyproject.toml` and CI.
- `README.md` names `*-lint.yml` workflows that no longer exist; everything runs in `main.yml`.

## Where to dig

There are no design docs in the repo. Commit bodies carry the why: `git log -S` or `--grep` on a behaviour before changing it.
