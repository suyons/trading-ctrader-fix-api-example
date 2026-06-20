# trading-ctrader-fix-api-example

A small, self-contained example of trading on **cTrader over the FIX 4.4 API**,
driven by a **multi-timeframe RSI** strategy. It is a fork of
[ejtraderLabs/ejtraderCT](https://github.com/ejtraderLabs/ejtraderCT) — the FIX
session code originates there; this repo trims it down and adds a clean,
testable decision engine.

> Earlier versions received trade signals as TradingView webhooks (behind nginx)
> and forwarded a Telegram notification per order. That plumbing is gone: the bot
> now makes its own decisions, so there is no web server and no Telegram.

## The strategy

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

See [`src/ctrader_fix/strategy.py`](src/ctrader_fix/strategy.py) for the
implementation.

## Project layout

```
config.py          Load FIX credentials from .env (fails fast if missing)
strategy.py        Multi-timeframe RSI decision engine (BUY / SELL / HOLD)
example_trade.py   Runnable example: evaluate the strategy, optionally trade
ctrader_client.py  High-level client: buy/sell/limit/positions/orders
fix_protocol.py    Raw FIX 4.4 session (logon, market data, order entry)
stream_buffer.py   Byte buffer that reassembles FIX messages off the socket
symbols.py         Default symbol id / pip-position reference table
calculations.py    Spread, pip value and commission helpers
tests/
  test_strategy.py   Behaviour checks for the decision engine
```

## Setup

This project uses [uv](https://docs.astral.sh/uv/) and `pyproject.toml`.

```bash
uv sync                       # create the venv and install dependencies
cp .env.example .env          # then fill in your cTrader FIX credentials
```

`.env` holds your credentials and is git-ignored — never commit it.

## Usage

```bash
uv run python example_trade.py   # evaluate the strategy and print the signal
```

By default it only prints the decision. To actually place orders, set
`CTRADER_LIVE_TRADING=true` in `.env` (and supply a real OHLC feed — see the note
in `example_trade.py`).

Using the pieces directly:

```python
from strategy import MultiTimeframeRsiStrategy, Signal
from ctrader_client import Ctrader
from config import load_config

strategy = MultiTimeframeRsiStrategy()
signal = strategy.decide(entry_closes, trend_closes)   # closes oldest -> newest

if signal is not Signal.HOLD:
    config = load_config()
    client = Ctrader(config.host, config.sender_comp_id, config.password)
    (client.buy if signal is Signal.BUY else client.sell)("EURUSD", 0.01, 0, 0)
```

## Tests

```bash
uv run pytest                 # or: python tests/test_strategy.py
```

## Credits

Forked from [ejtraderLabs/ejtraderCT](https://github.com/ejtraderLabs/ejtraderCT).
The FIX protocol layer is derived from that project.
