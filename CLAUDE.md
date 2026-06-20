# CLAUDE.md

Guidance for Claude Code working in this repository.

## ⚠️ This is a PUBLIC repository

- **Never commit secrets or personal data.** No passwords, account numbers,
  SenderCompIDs, hosts tied to an account, emails, or broker specifics.
- Real credentials live only in `.env`, which is **git-ignored**. Before every
  commit, confirm `.env` is not staged (`git status -s` must not list it).
- `.env.example` holds **placeholders only** — keep it that way.

## What this is

A small, educational example of trading on **cTrader over the FIX 4.4 API**,
driven by a **multi-timeframe RSI** strategy. Fork of
[ejtraderLabs/ejtraderCT](https://github.com/ejtraderLabs/ejtraderCT) (the FIX
protocol layer derives from it). No TradingView webhook, no web server, no
Telegram — it connects straight to the broker, decides, and optionally trades.

## Commands

```bash
uv sync --extra dev                 # create venv + install deps (incl. pytest)
uv run pytest -q                    # full test suite
uv run python src/main.py           # run the pipeline (offline by default)
```

- Tooling: **uv + pyproject.toml**. The project is a **non-package app**
  (`[tool.uv] package = false`); there is nothing to build/install.
- Tests resolve imports via `[tool.pytest.ini_options] pythonpath = ["src"]`.

## Layout & architecture

Flat modules under `src/` (no package wrapper); **absolute imports** between them
(`from strategy import ...`, not `from .strategy`).

```
src/
  main.py            Orchestrator: fetch OHLCV -> decide -> execute
  config.py          Load FIX credentials from .env (fails fast if missing)
  market_data.py     Tick -> candle aggregation + providers
  strategy.py        Multi-timeframe RSI decision engine (BUY / SELL / HOLD)
  ctrader_client.py  High-level client: buy/sell/limit/positions/orders
  fix_protocol.py    Raw FIX 4.4 session (logon, market data, order entry)
  stream_buffer.py   Byte buffer reassembling FIX messages off the socket
  symbols.py         Default symbol id / pip-position reference table
  calculations.py    Spread, pip value, commission helpers
tests/               test_strategy / test_pipeline / test_market_data / test_login_timeout
```

Pipeline: `market_data` (fetch) → `strategy` (decide) → `ctrader_client`
(execute), wired by `main.py`. Each module owns one responsibility.

## Key behaviors & constraints

- **Config** comes from env / `.env` via `python-dotenv`. Variable **names**
  (public): `CTRADER_HOST`, `CTRADER_SENDER_COMP_ID`, `CTRADER_PASSWORD`,
  `CTRADER_USE_SSL`, `CTRADER_CURRENCY`. `load_config()` raises if a required one
  is missing.
- **TLS by default** (`CTRADER_USE_SSL=true`): QUOTE/TRADE ports 5211/5212;
  plain text is 5201/5202. Ports are picked from `FIX_PORTS[use_ssl]`.
- **No history endpoint.** cTrader FIX streams spot ticks only. `FixCandleFeed`
  aggregates ticks into OHLCV candles *forward* from subscription (no backfill),
  so it suits low timeframes over a session, not deep history / high timeframes.
  `SampleMarketData` provides synthetic closes for offline runs. Candle `volume`
  is the tick count (FIX top-of-book has no traded volume).
- **Bounded login.** `Ctrader(..., login_timeout=15)` bounds connect + login and
  raises `TimeoutError` instead of hanging (e.g. closed market / unreachable
  broker). The constructor closes sockets and re-raises rather than swallowing.
- **Daemon threads.** All FIX worker threads (quote/trade readers, security
  list, heartbeats) are daemon, so the process exits immediately.
- The strategy needs deep history (default 200 closes on 5m and 4h), which live
  tick aggregation cannot supply quickly — so `main.py` defaults to
  `SampleMarketData`. A real history provider would plug into `fetch_closes`.

## Conventions

- Keep modules small, single-responsibility; absolute imports; descriptive
  names. Match the surrounding style.
- Intentional shortcuts are marked with `ponytail:` comments naming the ceiling.
- Non-trivial logic ships with a runnable check under `tests/` (no heavy
  fixtures; deterministic, fast).
- Commit messages explain the *why*; commit/push only the relevant change set.
  Markets are closed on weekends, so live FIX validation needs market hours.
