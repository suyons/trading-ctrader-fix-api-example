"""Runnable example: evaluate the strategy and (optionally) route it to cTrader.

    uv run ctrader-example

Loads credentials from .env, evaluates :class:`MultiTimeframeRsiStrategy` on a
set of closing prices, prints the resulting signal, and — only when
``CTRADER_LIVE_TRADING=true`` — connects over FIX and places the order.

Decision is intentionally decoupled from market data: feed it closes from any
source. ponytail: the sample closes below are placeholders. Wire your own OHLC
feed (broker history API / candle store) — the FIX session here streams spot
ticks, not candles, so it cannot build RSI on its own. Upgrade path: add a
candle source and replace ``sample_*_closes``.
"""

import logging
import os

from config import load_config
from strategy import MultiTimeframeRsiStrategy, Signal

SYMBOL = "EURUSD"
VOLUME = 0.01


def sample_entry_closes() -> list[float]:
    """Placeholder 5-minute closes. Replace with a real feed."""
    return [1.0850 + 0.0001 * i for i in range(40)]


def sample_trend_closes() -> list[float]:
    """Placeholder 4-hour closes. Replace with a real feed."""
    return [1.0700 + 0.0005 * i for i in range(40)]


def route_signal(client, signal: Signal) -> None:
    if signal is Signal.BUY:
        client.buy(SYMBOL, VOLUME, 0, 0)
    elif signal is Signal.SELL:
        client.sell(SYMBOL, VOLUME, 0, 0)


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    strategy = MultiTimeframeRsiStrategy()
    signal = strategy.decide(sample_entry_closes(), sample_trend_closes())
    print(f"{SYMBOL} signal: {signal.value}")

    if os.environ.get("CTRADER_LIVE_TRADING", "").lower() != "true":
        print("Live trading disabled (set CTRADER_LIVE_TRADING=true to place orders).")
        return

    from ctrader_client import Ctrader

    config = load_config()
    client = Ctrader(
        config.host, config.sender_comp_id, config.password, config.currency
    )
    route_signal(client, signal)


if __name__ == "__main__":
    main()
