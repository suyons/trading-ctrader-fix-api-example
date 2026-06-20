"""Behaviour checks for the tick-based momentum strategy.

Deterministic, offline. Run with ``uv run pytest`` (or this file directly).
"""

import pytest

from strategy import Signal, TickMomentumStrategy


def feed(strategy, ticks):
    """Feed (bid, ask) ticks; return the list of resulting signals."""
    return [strategy.update(bid, ask) for bid, ask in ticks]


def quote(mid, spread=0.0001):
    return (mid - spread / 2, mid + spread / 2)


def test_warmup_holds_until_slow_period():
    strategy = TickMomentumStrategy(fast_period=5, slow_period=20)
    signals = feed(strategy, [quote(1.1000) for _ in range(20)])
    assert all(s is Signal.HOLD for s in signals)


def test_buy_on_upward_crossover():
    strategy = TickMomentumStrategy(fast_period=5, slow_period=20)
    flat = [quote(1.1000) for _ in range(25)]      # warm up, fast == slow
    rising = [quote(1.1000 + 0.0002 * i) for i in range(1, 30)]
    signals = feed(strategy, flat + rising)
    assert Signal.BUY in signals
    assert Signal.SELL not in signals


def test_sell_on_downward_crossover():
    strategy = TickMomentumStrategy(fast_period=5, slow_period=20)
    flat = [quote(1.1000) for _ in range(25)]
    falling = [quote(1.1000 - 0.0002 * i) for i in range(1, 30)]
    signals = feed(strategy, flat + falling)
    assert Signal.SELL in signals
    assert Signal.BUY not in signals


def test_wide_spread_suppresses_signal():
    strategy = TickMomentumStrategy(fast_period=5, slow_period=20)
    flat = [quote(1.1000) for _ in range(25)]
    # Same upward move, but the spread is blown out on every tick.
    rising_wide = [quote(1.1000 + 0.0002 * i, spread=0.0020) for i in range(1, 30)]
    signals = feed(strategy, flat + rising_wide)
    assert Signal.BUY not in signals and Signal.SELL not in signals


def test_rejects_bad_periods():
    with pytest.raises(ValueError):
        TickMomentumStrategy(fast_period=50, slow_period=20)


if __name__ == "__main__":
    import sys

    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except (AssertionError, Exception) as error:  # noqa: BLE001
                failures += 1
                print(f"FAIL {name}: {error}")
    sys.exit(1 if failures else 0)
