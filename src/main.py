"""Entry point: stream FIX ticks -> tick strategy -> execute (FIX only).

    uv run python src/main.py

A pure FIX pipeline: subscribe to the live bid/ask quote stream, feed every tick
to :class:`TickMomentumStrategy`, and route BUY/SELL to the FIX trade session. No
candles, no history, no external data — the point is to exercise the cTrader FIX
API as the tick-based, low-latency interface it is. Run against a demo account.
"""

import logging
import time

from config import load_config
from ctrader_client import Ctrader
from strategy import Signal, TickMomentumStrategy

SYMBOL = "EURUSD"
VOLUME = 0.01


def stream_ticks(client, symbol: str, poll_interval: float = 0.05):
    """Yield (bid, ask) for each new quote on the FIX spot stream.

    ponytail: polls ``client.quote`` at ``poll_interval`` and dedupes; this can
    miss ticks between polls. For true HFT, hook the FIX market-data callback
    directly instead of polling.
    """
    client.subscribe(symbol)
    last = None
    while True:
        quote = client.quote(symbol)
        if isinstance(quote, dict) and "bid" in quote and "ask" in quote:
            tick = (quote.get("time"), quote["bid"], quote["ask"])
            if tick != last:
                last = tick
                yield quote["bid"], quote["ask"]
        time.sleep(poll_interval)


def execute(client, signal: Signal, symbol: str, volume: float) -> None:
    if signal is Signal.BUY:
        client.buy(symbol, volume, 0, 0)
    elif signal is Signal.SELL:
        client.sell(symbol, volume, 0, 0)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    client = Ctrader(
        config.host,
        config.sender_comp_id,
        config.password,
        config.currency,
        use_ssl=config.use_ssl,
    )

    strategy = TickMomentumStrategy()
    for bid, ask in stream_ticks(client, SYMBOL):
        signal = strategy.update(bid, ask)
        if signal is not Signal.HOLD:
            logging.info("%s signal %s @ bid=%s ask=%s", SYMBOL, signal.value, bid, ask)
            execute(client, signal, SYMBOL, VOLUME)


if __name__ == "__main__":
    main()
