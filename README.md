# Algo Trading — cTrader FIX API Example

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Packaging](https://img.shields.io/badge/packaging-uv-purple)
![Protocol](https://img.shields.io/badge/protocol-FIX%204.4-green)
![Transport](https://img.shields.io/badge/transport-TLS-success)

A small, self-contained example of trading on **cTrader over the FIX 4.4 API**,
driven by a **multi-timeframe RSI** strategy. It connects directly to a broker's
cTrader FIX endpoints — no TradingView webhook, no web server, no third-party
relay — evaluates a signal, and (optionally) places the order itself.

> **Heads up — this is an educational example.** Start with a *demo* account.
> Read the [disclaimer](#disclaimer) before pointing it at real money.

## Features

- 🔌 **Pure-stdlib FIX 4.4 client** for cTrader (QUOTE + TRADE sessions).
- 🕯️ **Tick → candle aggregation** — build live OHLCV bars from the FIX quote
  stream (`FixCandleFeed`), or run offline with synthetic data.
- 🔒 **TLS by default** (ports 5211/5212), with a one-line fallback to plain text.
- 📈 **Multi-timeframe RSI strategy** as a small, pure, unit-tested function.
- 🧪 **Backtest engine** — walk an OHLCV series bar by bar (no lookahead) and
  report trades, win rate, return, profit factor and drawdown.
- 🧩 **Decoupled pipeline** — `main.py` orchestrates *fetch → decide → execute*,
  one module per responsibility; bring your own candle feed.
- 🔑 **`.env`-based credentials** laid out to mirror the cTrader FIX API panel.

## The example strategy

The decision engine reproduces the "Multi Timeframe RSI" indicator the project
grew from. Two timeframes, one role each:

- **Trend timeframe** (default 4h) classifies the trend via `RSI > 50`.
- **Entry timeframe** (default 5m) spots the turn via an RSI crossover.

```
BUY  when RSI(trend) > 50   and RSI(entry) crosses up   the oversold line (40)
SELL when RSI(trend) < 50   and RSI(entry) crosses down the overbought line (60)
```

The first condition filters for trend direction; the second times the entry on an
oversold/overbought reversal. RSI uses Wilder's smoothing, matching TradingView's
`ta.rsi`, so signals line up with the chart below. Each horizontal line is one
limit order plotted on `OANDA:EURUSD`:

![EURUSD image](docs/EURUSD_2024-05-22_12-58-35.png)

## Project layout

```
src/
  main.py            Orchestrator: fetch OHLCV -> decide -> execute
  config.py          Load FIX credentials from .env (fails fast if missing)
  market_data.py     Tick -> candle aggregation + providers (FixCandleFeed / sample)
  strategy.py        Multi-timeframe RSI decision engine (BUY / SELL / HOLD)
  backtest.py        Replay the strategy over a historical OHLCV series
  history.py         Fetch real historical bars (Yahoo Finance, no API key)
  ctrader_client.py  High-level client: buy/sell/limit/positions/orders
  fix_protocol.py    Raw FIX 4.4 session (logon, market data, order entry)
  stream_buffer.py   Byte buffer that reassembles FIX messages off the socket
  symbols.py         Default symbol id / pip-position reference table
  calculations.py    Spread, pip value and commission helpers
tests/
  test_market_data.py  Tick -> candle aggregation checks
  test_backtest.py   Backtest engine checks
  test_strategy.py   Behaviour checks for the decision engine
  test_pipeline.py   Wiring check: sample data -> strategy -> signal
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
uv run python src/main.py   # fetch data, evaluate the strategy, act on the signal
```

`main.py` runs the full pipeline — **fetch** OHLCV closes (`market_data.py`),
**decide** with the multi-timeframe RSI strategy (`strategy.py`), and on a `BUY`
or `SELL` signal **execute** the order over FIX (`ctrader_client.py`). Out of the
box it uses `SampleMarketData` (synthetic closes) so it runs offline; swap in a
real provider in `src/market_data.py` and point it at a **demo** account.

Using the pieces directly:

```python
from strategy import MultiTimeframeRsiStrategy, Signal
from ctrader_client import Ctrader
from config import load_config

strategy = MultiTimeframeRsiStrategy()
signal = strategy.decide(entry_closes, trend_closes)   # closes oldest -> newest

if signal is not Signal.HOLD:
    config = load_config()
    client = Ctrader(
        config.host, config.sender_comp_id, config.password, use_ssl=config.use_ssl
    )
    (client.buy if signal is Signal.BUY else client.sell)("EURUSD", 0.01, 0, 0)
```

### Live OHLCV from FIX ticks

`FixCandleFeed` subscribes to the live FIX quote stream and aggregates ticks into
OHLCV candles. It returns the same `fetch_closes` interface, so it drops straight
into the pipeline:

```python
from ctrader_client import Ctrader
from market_data import FixCandleFeed
from config import load_config

config = load_config()
client = Ctrader(config.host, config.sender_comp_id, config.password,
                 use_ssl=config.use_ssl)
feed = FixCandleFeed(client)

candles = feed.fetch_ohlcv("XAUUSD", "1m", count=10)   # latest 10 one-minute bars
for c in candles:
    print(c.timestamp, c.open, c.high, c.low, c.close, c.volume)
```

> **Ceiling:** ticks only aggregate *forward* from the moment you subscribe —
> there is no backfill — so `fetch_ohlcv(count=10)` blocks for ~10 minutes while
> ten 1m bars form, and only works while the market is open. It suits low
> timeframes over a session, not deep history or high timeframes (200× 4h bars
> would take weeks). For those, plug a real history API into the same interface.
> Volume is the tick count, since FIX top-of-book carries no traded volume.

`Ctrader(...)` bounds connect + login by `login_timeout` (default 15s) and raises
`TimeoutError` if it doesn't complete — so a closed market or unreachable broker
fails fast instead of hanging.

## Tests

```bash
uv run pytest                                    # full suite
PYTHONPATH=src uv run python tests/test_strategy.py   # zero-dependency self-check
```

## Backtest

`src/backtest.py` walks a historical OHLCV series bar by bar, reusing the live
decision rule with no lookahead (the trend RSI at each bar is built only from 4h
blocks that have already closed, bucketed by real timestamp). Position model:
*flip on opposite signal* — long until a SELL, short until a BUY, no pyramiding —
and the open position is closed on the final bar.

```bash
uv run python src/backtest.py
```

Real prices come from Yahoo Finance via `src/history.py` (`EURUSD=X`, stdlib
`urllib`, no API key). Yahoo only retains intraday data for ~60 days, so for
windows older than that the fetch fails and the backtest falls back to a
deterministic synthetic series — the engine is identical either way.

Result for **2026-05-01 → 2026-05-29** — **real EURUSD 5m data** (entry 5m /
trend 4h, RSI 21, oversold 40 / mid 50 / overbought 60), fetched 2026-06-20:

| Metric            | Value     |
| ----------------- | --------: |
| Bars (5m closes)  | 5880      |
| Trades            | 9         |
| Win rate          | 22.2%     |
| Total return      | −0.28%    |
| Profit factor     | 0.78      |
| Max drawdown      | 0.66%     |

> ⚠️ Illustrative, not advice. This is a single instrument over a short window
> with **no spread/commission/slippage** modelled and a naive flip-on-signal exit
> — it is not evidence of an edge. The slightly negative return is unsurprising:
> a plain RSI mean-reversion rule with no costs hovers near break-even. Use it to
> validate the pipeline, then test your own rules, costs, and timeframes.

## Disclaimer

This project is provided **for educational purposes only** and comes with **no
warranty**. Automated trading carries substantial risk of loss; you are solely
responsible for any orders it sends. Always test against a **demo account**
first, and never trade money you can't afford to lose. Nothing here is financial
advice.

## Credits

Forked from [ejtraderLabs/ejtraderCT](https://github.com/ejtraderLabs/ejtraderCT);
the FIX protocol layer is derived from that project. See the
[cTrader FIX API documentation](https://help.ctrader.com/fix/) for protocol
details.
