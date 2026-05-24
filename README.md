# Agentic Trading System

A multi-agent stock trading system, built as a realistic demo for agentic AI software development. Four AI traders — Warren, George, Ray, and Cathie — each start with $100K in virtual capital, independently research the market, and make BUY / SELL / HOLD decisions. The agents are written in Python on the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) and use Brave Search + Fetch MCP servers for web research. A Java Spring Boot backend owns accounts, trade execution, and the audit trail; a React dashboard renders performance, runs, and per-cycle audit views.

## Quickstart

Requirements: Docker with the Compose plugin, or Podman 5+ (`podman compose` delegates to `docker-compose` and works the same; `podman-compose` also works).

```bash
git clone https://github.com/vasilkosturski/agentic-trading-system.git
cd agentic-trading-system
cp .env.example .env
# Open .env and fill in OPENAI_API_KEY and BRAVE_API_KEY at minimum.
docker compose up --build    # or: podman compose up --build
```

Once everything is healthy:

- Dashboard — http://localhost:5173
- Backend API — http://localhost:8080
- PostgreSQL — `localhost:5432` (user: `trading_user`, password: `trading_password`, database: `agentic_trading`)

Schemas (`agents`, `trading`, `analytics`) are created automatically by the backend on first boot via JPA's `hbm2ddl.create_namespaces`. The agents container then runs trading cycles on the cadence set by `RUN_EVERY_N_MINUTES` (default 480 — lower it in `.env` if you want to see activity sooner).

See [`.env.example`](.env.example) for what each variable does and where to get the API keys.

## Architecture

The system is full-stack: Python agents on the OpenAI Agents SDK driving a two-agent pipeline (Market Analyst → Decision Maker), a Java Spring Boot backend for stateful concerns (accounts, trade execution, run/audit persistence, prompt composition, WebSocket broadcasting), a React + TypeScript dashboard, and PostgreSQL for persistence across three schemas. The Market Analyst and Decision Maker both use Brave Search and Fetch via MCP for web research; Finnhub.io feeds market quotes through the backend's price cache.

## Get Involved

This project is a vehicle for learning and developing agentic systems — a space the industry is still collectively figuring out. It's a work in progress, with room for improvement across design, code quality, and ideas I haven't considered yet. If you want to comment, open an issue, send a pull request, or use the repo as a starting point to research and explore new directions for educational purposes, you're welcome to jump in.

## Disclaimers

While people have found the traders' market research generally helpful, **this is not investment advice**. The system trades with virtual capital — no real money is at stake. It's a demo, and some details may change as the system develops; check the repo for the current state.

## License

[MIT](LICENSE).
