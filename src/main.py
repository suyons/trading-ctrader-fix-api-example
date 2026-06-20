"""Entry point: orchestrate fetch OHLCV -> decide -> execute.

    uv run python src/main.py

Wires the three responsibilities together, one module each:
    market_data.MarketDataProvider     fetch OHLCV closes
    strategy.MultiTimeframeRsiStrategy  make the BUY / SELL / HOLD decision
    ctrader_client.Ctrader              execute the trade over FIX

Out of the box it uses ``SampleMarketData`` so the pipeline runs offline; swap in
a real provider (see ``market_data.py``) and point it at a demo account.
"""

import logging

from config import load_config
from market_data import MarketDataProvider, SampleMarketData
from strategy import MultiTimeframeRsiStrategy, Signal

SYMBOL = "EURUSD"
VOLUME = 0.01
ENTRY_TIMEFRAME = "5m"
TREND_TIMEFRAME = "4h"
HISTORY = 200  # closes per timeframe — enough to warm up the RSI


def decide_signal(market_data: MarketDataProvider) -> Signal:
    entry_closes = market_data.fetch_closes(SYMBOL, ENTRY_TIMEFRAME, HISTORY)
    trend_closes = market_data.fetch_closes(SYMBOL, TREND_TIMEFRAME, HISTORY)
    return MultiTimeframeRsiStrategy().decide(entry_closes, trend_closes)


def execute_trade(signal: Signal) -> None:
    from ctrader_client import Ctrader

    config = load_config()
    client = Ctrader(
        config.host,
        config.sender_comp_id,
        config.password,
        config.currency,
        use_ssl=config.use_ssl,
    )
    if signal is Signal.BUY:
        client.buy(SYMBOL, VOLUME, 0, 0)
    elif signal is Signal.SELL:
        client.sell(SYMBOL, VOLUME, 0, 0)


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    signal = decide_signal(SampleMarketData())
    print(f"{SYMBOL} signal: {signal.value}")

    if signal is Signal.HOLD:
        return
    execute_trade(signal)


if __name__ == "__main__":
    main()
