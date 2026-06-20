# Algo Trading — cTrader FIX API Example

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Packaging](https://img.shields.io/badge/packaging-uv-purple)
![Protocol](https://img.shields.io/badge/protocol-FIX%204.4-green)
![Transport](https://img.shields.io/badge/transport-TLS-success)

A small, self-contained **tick-based** trading bot on **cTrader over the FIX 4.4
API**. It connects straight to a broker's FIX endpoints, streams live bid/ask
quotes, makes a decision **on every tick**, and routes orders over the same FIX
session — no candles, no history, no external data, no web server.

> **Heads up — this is an educational example.** Start with a *demo* account.
> Read the [disclaimer](#disclaimer) before pointing it at real money.

## Why tick-based?

cTrader's FIX API is built for what FIX does well: **low-latency streaming quotes
and order execution**. It deliberately has **no historical-bar endpoint** — that
is the job of cTrader's *Open API*. Rather than bolt external OHLCV history onto a
FIX client, this repo leans into the protocol's nature: a strategy that reacts to
the raw tick stream and executes immediately. See the
[cTrader FIX API docs](https://help.ctrader.com/fix/).

## Features

- 🔌 **Pure-stdlib FIX 4.4 client** for cTrader (QUOTE + TRADE sessions).
- ⚡ **Tick-driven strategy** — reacts to every bid/ask quote; no candles, no
  history, no external data feed.
- 🛡️ **Spread-aware** — suppresses signals when the book is too wide to act on,
  a microstructure guard a candle strategy can't make.
- 🔒 **TLS by default** (ports 5211/5212), with a one-line fallback to plain text.
- ⏱️ **Bounded login** — raises `TimeoutError` instead of hanging on a closed
  market or unreachable broker.
- 🔑 **`.env`-based credentials** laid out to mirror the cTrader FIX API panel.

## The strategy

`TickMomentumStrategy` (in `src/strategy.py`) is fed one `(bid, ask)` tick at a
time and returns `BUY` / `SELL` / `HOLD`. All state updates per tick, on the
mid-price:

- a **fast** and a **slow** EMA of the mid-price — a zero-crossing of
  `fast − slow` is the directional signal (fast crosses above → BUY, below →
  SELL);
- an **EMA of the spread** as a guard — a signal is dropped when the current
  spread is wider than `spread_tolerance ×` its recent average.

It warms up from the live stream itself (no history needed) — signals only start
once enough ticks have passed. It is illustrative of the FIX *tick → decide →
execute* loop, **not** a tuned alpha.

## Project layout

```
src/
  main.py            Orchestrator: stream FIX ticks -> decide -> execute
  config.py          Load FIX credentials from .env (fails fast if missing)
  strategy.py        Tick momentum strategy (BUY / SELL / HOLD) — FIX-only
  ctrader_client.py  High-level client: buy/sell/limit/positions/orders
  fix_protocol.py    Raw FIX 4.4 session (logon, market data, order entry)
  stream_buffer.py   Byte buffer that reassembles FIX messages off the socket
tests/
  test_strategy.py       Tick strategy behaviour checks
  test_tick_stream.py    FIX tick-stream helper check
  test_login_timeout.py  Login bounded-timeout check
```

## Prerequisites

- **Python 3.10+** and [uv](https://docs.astral.sh/uv/).
- A **cTrader account** (start with a demo) at a broker that offers the FIX API.
- **FIX API enabled** for that account — in cTrader: *Settings → FIX API*. That
  page shows the Host, Password and SenderCompID you'll paste into `.env`.

## Setup

```bash
uv sync                       # create the venv and install dependencies
cp .env.example .env          # then fill in your cTrader FIX credentials
```

`.env` holds your credentials and is git-ignored — never commit it.

## Configuration

All configuration lives in `.env`. The template (`.env.example`) is laid out to
match the two connection blocks shown in cTrader's *Settings → FIX API* panel —
both blocks share the same Host, Password and SenderCompID, so you copy those
three values across.

| Variable                 | Required | Default | Description                                                        |
| ------------------------ | :------: | :-----: | ------------------------------------------------------------------ |
| `CTRADER_HOST`           |    ✅    |    —    | FIX host name, e.g. `demo-xx.p.c-trader.com`                       |
| `CTRADER_SENDER_COMP_ID` |    ✅    |    —    | Account / SenderCompID, e.g. `demo.broker.1234567`                 |
| `CTRADER_PASSWORD`       |    ✅    |    —    | Your FIX API / account password                                    |
| `CTRADER_USE_SSL`        |    —     | `true`  | `true` → TLS ports 5211/5212, `false` → plain text 5201/5202       |
| `CTRADER_CURRENCY`       |    —     | `USD`   | Account deposit currency                                           |

FIX ports, selected automatically from `CTRADER_USE_SSL`:

| Session         | TLS (default) | Plain text |
| --------------- | :-----------: | :--------: |
| QUOTE (prices)  |     5211      |    5201    |
| TRADE (orders)  |     5212      |    5202    |

## Usage

```bash
uv run python src/main.py   # stream ticks, evaluate the strategy, act on signals
```

`main.py` connects over FIX, subscribes to the live quote stream, and on **every
tick** feeds the strategy; a `BUY`/`SELL` routes to the FIX trade session. It runs
continuously while the market is open — point it at a **demo** account.

Using the pieces directly:

```python
from strategy import TickMomentumStrategy, Signal

strategy = TickMomentumStrategy()
for bid, ask in tick_source:          # e.g. main.stream_ticks(client, "EURUSD")
    signal = strategy.update(bid, ask)
    if signal is not Signal.HOLD:
        ...                           # route to client.buy / client.sell
```

`Ctrader(...)` bounds connect + login by `login_timeout` (default 15s) and raises
`TimeoutError` if it doesn't complete — so a closed market or unreachable broker
fails fast instead of hanging.

## Tests

```bash
uv run pytest                                    # full suite
PYTHONPATH=src uv run python tests/test_strategy.py   # zero-dependency self-check
```

## Disclaimer

This project is provided **for educational purposes only** and comes with **no
warranty**. Automated trading — and tick strategies especially — carries
substantial risk of loss; you are solely responsible for any orders it sends.
Always test against a **demo account** first, and never trade money you can't
afford to lose. Nothing here is financial advice.

## Credits

Forked from [ejtraderLabs/ejtraderCT](https://github.com/ejtraderLabs/ejtraderCT)
("Perfect for HFT"); the FIX protocol layer is derived from that project. See the
[cTrader FIX API documentation](https://help.ctrader.com/fix/) for protocol
details.
