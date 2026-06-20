"""Market data: provide OHLCV closing prices per symbol and timeframe.

This is the data seam of the pipeline. cTrader's FIX API streams spot ticks, not
historical candles, so OHLC bars must come from elsewhere — your broker's REST /
history API, a candle store, or by aggregating ticks yourself. Implement
``fetch_closes`` against that source and the strategy/execution layers are
unaffected.
"""

from typing import Protocol


class MarketDataProvider(Protocol):
    """Anything that can supply closing prices for a symbol/timeframe."""

    def fetch_closes(self, symbol: str, timeframe: str, count: int) -> list[float]:
        """Return the latest ``count`` closing prices, oldest -> newest."""


class SampleMarketData:
    """Synthetic provider so the pipeline runs offline, end to end.

    ponytail: returns generated closes, not live prices. Swap for a real
    provider with the same ``fetch_closes`` signature before trading — cTrader
    FIX has no history endpoint, so source candles from your broker's REST /
    history API or aggregate ticks yourself.
    """

    _BASE = {"5m": 1.0850, "4h": 1.0700}
    _STEP = {"5m": 0.0001, "4h": 0.0005}

    def fetch_closes(self, symbol: str, timeframe: str, count: int) -> list[float]:
        base = self._BASE.get(timeframe, 1.0)
        step = self._STEP.get(timeframe, 0.0001)
        return [base + step * index for index in range(count)]
