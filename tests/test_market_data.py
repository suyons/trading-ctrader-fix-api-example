"""Deterministic checks for tick -> candle aggregation.

No network: synthetic XAUUSD ticks stand in for a live FIX stream so we can prove
the aggregator yields a correct OHLCV list. Run with ``uv run pytest``.
"""

from market_data import CandleAggregator, Candle

MINUTE = 60
BASE_TS = (1_700_000_000 // MINUTE) * MINUTE  # aligned to a minute boundary
GOLD = 2330.0


def synthetic_gold_ticks(minutes: int):
    """Yield (timestamp, price) ticks for `minutes` one-minute buckets.

    Each minute gets four ticks shaped so OHLC is predictable:
    open=base, then a high, then a low, then close=base+0.5.
    """
    for minute in range(minutes):
        base = GOLD + minute  # a distinct level per minute
        start = BASE_TS + minute * MINUTE
        for offset, price in ((0, base), (10, base + 1.5), (20, base - 1.0), (50, base + 0.5)):
            yield start + offset, price


def build(minutes: int) -> CandleAggregator:
    aggregator = CandleAggregator(MINUTE)
    for timestamp, price in synthetic_gold_ticks(minutes):
        aggregator.add_tick(timestamp, price)
    return aggregator


def test_fetch_latest_10_xauusd_1m_candles():
    # 12 buckets of ticks -> 11 complete + 1 still forming.
    candles = build(12).latest(10)

    assert len(candles) == 10
    assert all(isinstance(c, Candle) for c in candles)
    # "Latest 10 complete" = buckets 1..10 (bucket 11 is still forming).
    assert [c.timestamp for c in candles] == [BASE_TS + m * MINUTE for m in range(1, 11)]


def test_ohlcv_values_are_correct():
    candle = build(3).completed_candles()[0]  # first complete bucket (minute 0)
    assert (candle.open, candle.high, candle.low, candle.close) == (
        GOLD, GOLD + 1.5, GOLD - 1.0, GOLD + 0.5,
    )
    assert candle.volume == 4  # four ticks aggregated


def test_high_low_bound_open_close():
    for candle in build(12).completed_candles():
        assert candle.high >= max(candle.open, candle.close)
        assert candle.low <= min(candle.open, candle.close)
