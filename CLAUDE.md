# CLAUDE.md

Guidance for Claude Code working in this repository.

## ⚠️ This is a PUBLIC repository

- **Never commit secrets or personal data.** No passwords, account numbers,
  SenderCompIDs, hosts tied to an account, emails, or broker specifics.
- Real credentials live only in `.env`, which is **git-ignored**. Before every
  commit, confirm `.env` is not staged (`git status -s` must not list it).
- `.env.example` holds **placeholders only** — keep it that way.

## What this is

A small, educational **tick-based** trading bot on **cTrader over the FIX 4.4
API**. Fork of [ejtraderLabs/ejtraderCT](https://github.com/ejtraderLabs/ejtraderCT)
(the FIX protocol layer derives from it). It streams live bid/ask quotes, decides
on **every tick**, and executes over the same FIX session — no candles, no
history, no external data, no web server. The repo deliberately leans into what
FIX is for (low-latency quotes + execution); OHLCV/history is out of scope (that
would be cTrader's Open API).

## Commands

```bash
uv sync --extra dev                 # create venv + install deps (incl. pytest)
uv run pytest -q                    # full test suite (offline)
uv run python src/main.py           # stream FIX ticks -> decide -> execute (needs market open)
```

- Tooling: **uv + pyproject.toml**. The project is a **non-package app**
  (`[tool.uv] package = false`); there is nothing to build/install.
- Tests resolve imports via `[tool.pytest.ini_options] pythonpath = ["src"]`.

## Layout & architecture

Flat modules under `src/` (no package wrapper); **absolute imports** between them
(`from strategy import ...`, not `from .strategy`).

```
src/
  main.py            Orchestrator: stream FIX ticks -> decide -> execute
  config.py          Load FIX credentials from .env (fails fast if missing)
  strategy.py        TickMomentumStrategy (per-tick BUY / SELL / HOLD) — FIX-only
  ctrader_client.py  High-level client: buy/sell/limit/positions/orders
  fix_protocol.py    Raw FIX 4.4 session (logon, market data, order entry)
  stream_buffer.py   Byte buffer reassembling FIX messages off the socket
  symbols.py         Default symbol id / pip-position reference table
  calculations.py    Spread, pip value, commission helpers
tests/               test_strategy / test_tick_stream / test_login_timeout
```

Loop: `main.stream_ticks` (FIX quote stream) → `strategy.update(bid, ask)`
(decide) → `ctrader_client` (execute). Each module owns one responsibility.

## Key behaviors & constraints

- **Config** comes from env / `.env` via `python-dotenv`. Variable **names**
  (public): `CTRADER_HOST`, `CTRADER_SENDER_COMP_ID`, `CTRADER_PASSWORD`,
  `CTRADER_USE_SSL`, `CTRADER_CURRENCY`. `load_config()` raises if a required one
  is missing.
- **TLS by default** (`CTRADER_USE_SSL=true`): QUOTE/TRADE ports 5211/5212;
  plain text is 5201/5202. Ports are picked from `FIX_PORTS[use_ssl]`.
- **Tick-based, no history.** cTrader FIX streams quotes only — there are no
  candles/bars. `TickMomentumStrategy.update(bid, ask)` runs per tick (fast/slow
  EMA crossover of the mid, plus an EMA-of-spread guard) and warms up from the
  live stream. `main.stream_ticks` polls `client.quote` and dedupes (ponytail:
  polling can miss ticks; hook the FIX market-data callback for true HFT).
- **Bounded login.** `Ctrader(..., login_timeout=15)` bounds connect + login and
  raises `TimeoutError` instead of hanging (e.g. closed market / unreachable
  broker). The constructor closes sockets and re-raises rather than swallowing.
- **Daemon threads.** All FIX worker threads (quote/trade readers, security
  list, heartbeats) are daemon, so the process exits immediately.

## Conventions

- Keep modules small, single-responsibility; absolute imports; descriptive
  names. Match the surrounding style.
- Intentional shortcuts are marked with `ponytail:` comments naming the ceiling.
- Non-trivial logic ships with a runnable check under `tests/` (no heavy
  fixtures; deterministic, fast). **Tests stay offline** — never hit the network.
- Commit messages explain the *why*; commit/push only the relevant change set.
  Markets are closed on weekends, so live FIX validation needs market hours.
