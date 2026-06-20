"""Market data: provide OHLCV candles / closing prices per symbol and timeframe.

cTrader's FIX API streams spot ticks, not historical candles. Two providers live
here behind one ``fetch_closes`` seam:

- :class:`FixCandleFeed` subscribes to a live FIX quote stream and aggregates the
  ticks into OHLCV candles as they arrive.
- :class:`SampleMarketData` returns synthetic closes so the pipeline runs offline.

ponytail: tick aggregation only builds candles *forward* from the moment you
subscribe — there is no backfill. It suits low timeframes over a session (e.g.
1m), not deep history or high timeframes (200x 4h bars would take weeks). For
that, plug a real history API into the same ``fetch_closes`` interface. Volume is
the tick count, since FIX top-of-book carries no traded volume.
"""

import time
from dataclasses import dataclass
from typing import Protocol

TIMEFRAME_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400}


@dataclass
class Candle:
    timestamp: int  # bucket start, epoch seconds
    open: float
    high: float
    low: float
    close: float
    volume: int  # tick count (FIX top-of-book has no traded volume)


class MarketDataProvider(Protocol):
    """Anything that can supply closing prices for a symbol/timeframe."""

    def fetch_closes(self, symbol: str, timeframe: str, count: int) -> list[float]:
        """Return the latest ``count`` closing prices, oldest -> newest."""


class CandleAggregator:
    """Pure OHLCV aggregation: feed it ticks, read back candles.

    A bucket is sealed once a tick lands in a later one, so all candles except the
    most recent (still-forming) one are complete.
    """

    def __init__(self, interval_seconds: int):
        self.interval = interval_seconds
        self._buckets: dict[int, Candle] = {}

    def add_tick(self, timestamp: float, price: float) -> None:
        start = int(timestamp // self.interval) * self.interval
        candle = self._buckets.get(start)
        if candle is None:
            self._buckets[start] = Candle(start, price, price, price, price, 1)
        else:
            candle.high = max(candle.high, price)
            candle.low = min(candle.low, price)
            candle.close = price
            candle.volume += 1

    def completed_candles(self) -> list[Candle]:
        ordered = [self._buckets[start] for start in sorted(self._buckets)]
        return ordered[:-1]  # drop the still-forming latest bucket

    def latest(self, count: int) -> list[Candle]:
        return self.completed_candles()[-count:]


class FixCandleFeed:
    """Build OHLCV candles from a live cTrader FIX quote subscription.

    Requires an open market — it streams ticks and aggregates forward, so
    ``fetch_ohlcv(count)`` blocks until ``count`` candles have formed (or it times
    out). The client is any object exposing ``subscribe(symbol)`` and
    ``quote(symbol) -> {"time", "bid", "ask"}`` (i.e. :class:`Ctrader`).
    """

    def __init__(self, client, poll_interval: float = 0.2):
        self._client = client
        self._poll = poll_interval

    def fetch_ohlcv(
        self, symbol: str, timeframe: str, count: int, timeout: float | None = None
    ) -> list[Candle]:
        interval = TIMEFRAME_SECONDS[timeframe]
        if timeout is None:
            timeout = (count + 2) * interval + 60
        aggregator = CandleAggregator(interval)
        self._client.subscribe(symbol)

        deadline = time.monotonic() + timeout
        last_tick = None
        while len(aggregator.completed_candles()) < count:
            if time.monotonic() >= deadline:
                formed = len(aggregator.completed_candles())
                raise TimeoutError(
                    f"only formed {formed}/{count} {timeframe} candles for {symbol} "
                    f"in {timeout:.0f}s (is the market open?)"
                )
            quote = self._client.quote(symbol)
            if isinstance(quote, dict) and "bid" in quote and "ask" in quote:
                tick = (quote.get("time"), quote["bid"], quote["ask"])
                if tick != last_tick:
                    last_tick = tick
                    mid = (quote["bid"] + quote["ask"]) / 2
                    aggregator.add_tick(time.time(), mid)
            time.sleep(self._poll)
        return aggregator.latest(count)

    def fetch_closes(self, symbol: str, timeframe: str, count: int) -> list[float]:
        return [candle.close for candle in self.fetch_ohlcv(symbol, timeframe, count)]


class SampleMarketData:
    """Synthetic provider so the pipeline runs offline, end to end.

    ponytail: returns generated closes, not live prices. Swap for
    :class:`FixCandleFeed` (live) or a real history API before trading.
    """

    _BASE = {"5m": 1.0850, "4h": 1.0700}
    _STEP = {"5m": 0.0001, "4h": 0.0005}

    def fetch_closes(self, symbol: str, timeframe: str, count: int) -> list[float]:
        base = self._BASE.get(timeframe, 1.0)
        step = self._STEP.get(timeframe, 0.0001)
        return [base + step * index for index in range(count)]
