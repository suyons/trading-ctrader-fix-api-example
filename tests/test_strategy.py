"""Behaviour checks for the multi-timeframe RSI decision engine.

Run with ``uv run pytest`` (or ``python -m pytest``).
"""

from ctrader_fix.strategy import MultiTimeframeRsiStrategy, Signal, rsi_series


def _rsi(values, length):
    return rsi_series(values, length)[-1]


def test_rsi_all_gains_is_100():
    closes = [float(i) for i in range(1, 20)]
    assert _rsi(closes, 14) == 100.0


def test_rsi_all_losses_is_zero():
    closes = [float(i) for i in range(20, 1, -1)]
    assert _rsi(closes, 14) == 0.0


def test_buy_on_uptrend_and_oversold_cross_up():
    # Trend timeframe trending up -> trend RSI > midline.
    trend = [1.0 + 0.01 * i for i in range(40)]
    # Entry timeframe: falls into oversold, then ticks up -> crosses oversold.
    entry = [1.0 - 0.01 * i for i in range(20)] + [0.81, 0.95]
    strategy = MultiTimeframeRsiStrategy(rsi_length=14)
    assert strategy.decide(entry, trend) is Signal.BUY


def test_hold_when_trend_disagrees():
    # Same oversold cross-up on entry, but trend timeframe is falling.
    trend = [1.0 - 0.01 * i for i in range(40)]
    entry = [1.0 - 0.01 * i for i in range(20)] + [0.81, 0.95]
    strategy = MultiTimeframeRsiStrategy(rsi_length=14)
    assert strategy.decide(entry, trend) is Signal.HOLD


def test_sell_on_downtrend_and_overbought_cross_down():
    trend = [2.0 - 0.01 * i for i in range(40)]
    entry = [1.0 + 0.01 * i for i in range(20)] + [1.19, 1.05]
    strategy = MultiTimeframeRsiStrategy(rsi_length=14)
    assert strategy.decide(entry, trend) is Signal.SELL


if __name__ == "__main__":
    import sys

    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except AssertionError as error:
                failures += 1
                print(f"FAIL {name}: {error}")
    sys.exit(1 if failures else 0)
