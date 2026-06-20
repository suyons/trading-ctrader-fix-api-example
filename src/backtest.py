"""Backtest the multi-timeframe RSI strategy over a historical OHLCV series.

    uv run python src/backtest.py

Walks the entry-timeframe bars in time order, reusing the live decision rule
(:meth:`MultiTimeframeRsiStrategy.signal_from_rsi`) with no lookahead — the trend
RSI at each bar is built only from higher-timeframe blocks that have already
closed (bucketed by real timestamp, so weekend gaps don't misalign it). Position
model: *flip on opposite signal* — long until a SELL, short until a BUY, no
pyramiding — and the open position is closed at the final bar.

Bars are ``(epoch_seconds, close)``. `main` pulls real EURUSD 5m data via
:mod:`history`; if that fails (e.g. outside Yahoo's ~60-day intraday window) it
falls back to a deterministic synthetic series so the command always runs.
"""

import bisect
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from history import fetch_bars
from strategy import MultiTimeframeRsiStrategy, Signal, rsi_series

ENTRY_SECONDS = 300  # 5m entry timeframe
TREND_SECONDS = 14400  # 4h trend timeframe
BARS_PER_DAY = 288  # 24h of 5-minute bars


@dataclass
class BacktestResult:
    trades: int
    wins: int
    win_rate: float
    total_return_pct: float
    profit_factor: float
    max_drawdown_pct: float


def synthetic_bars(
    start: date, end: date, *, seed: int = 20260501, start_price: float = 1.0800
) -> list[tuple[int, float]]:
    """Deterministic weekday 5m bars for [start, end] (forex is closed weekends).

    A seeded Gaussian random walk — stands in for a real history feed.
    """
    rng = random.Random(seed)
    bars: list[tuple[int, float]] = []
    price = start_price
    day = start
    while day <= end:
        if day.weekday() < 5:  # Mon-Fri
            day_start = int(
                datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp()
            )
            for step in range(BARS_PER_DAY):
                price *= 1 + rng.gauss(0, 0.0004)
                bars.append((day_start + step * ENTRY_SECONDS, price))
        day += timedelta(days=1)
    return bars


def _trend_blocks(bars, trend_seconds):
    """Resample bars into (bucket_id, close) per completed higher-timeframe block."""
    ids: list[int] = []
    closes: list[float] = []
    for timestamp, close in bars:
        bucket = timestamp // trend_seconds
        if ids and ids[-1] == bucket:
            closes[-1] = close
        else:
            ids.append(bucket)
            closes.append(close)
    return ids, closes


def run_backtest(
    bars: list[tuple[int, float]],
    strategy: MultiTimeframeRsiStrategy,
    trend_seconds: int = TREND_SECONDS,
) -> BacktestResult:
    length = strategy.rsi_length
    closes = [close for _, close in bars]
    if len(closes) <= length:
        return _summarize([])

    entry_rsi = rsi_series(closes, length)
    block_ids, block_closes = _trend_blocks(bars, trend_seconds)
    trend_rsi = rsi_series(block_closes, length) if len(block_closes) > length else []

    position = 0  # +1 long, -1 short, 0 flat
    entry_price = 0.0
    returns: list[float] = []

    for index in range(length + 1, len(closes)):
        # Latest trend block that has fully closed before this bar (no lookahead).
        block = bisect.bisect_left(block_ids, bars[index][0] // trend_seconds) - 1
        if block <= length or block >= len(trend_rsi) or trend_rsi[block] is None:
            continue
        signal = strategy.signal_from_rsi(
            trend_rsi[block], entry_rsi[index - 1], entry_rsi[index]
        )
        price = closes[index]
        if signal is Signal.BUY and position <= 0:
            if position < 0:
                returns.append((entry_price - price) / entry_price)
            position, entry_price = 1, price
        elif signal is Signal.SELL and position >= 0:
            if position > 0:
                returns.append((price - entry_price) / entry_price)
            position, entry_price = -1, price

    if position != 0:  # close the open position at the last bar
        last = closes[-1]
        pnl = (last - entry_price) if position > 0 else (entry_price - last)
        returns.append(pnl / entry_price)

    return _summarize(returns)


def _summarize(returns: list[float]) -> BacktestResult:
    if not returns:
        return BacktestResult(0, 0, 0.0, 0.0, 0.0, 0.0)

    wins = sum(1 for r in returns if r > 0)
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = -sum(r for r in returns if r < 0)

    equity, peak, max_dd = 1.0, 1.0, 0.0
    for r in returns:
        equity *= 1 + r
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak)

    return BacktestResult(
        trades=len(returns),
        wins=wins,
        win_rate=wins / len(returns),
        total_return_pct=(equity - 1) * 100,
        profit_factor=(gross_profit / gross_loss) if gross_loss else float("inf"),
        max_drawdown_pct=max_dd * 100,
    )


def _load_bars(symbol: str, start: date, end: date) -> tuple[list, str]:
    try:
        bars = fetch_bars(symbol, "5m", start, end)
        return bars, f"real {symbol} 5m via Yahoo Finance"
    except Exception as error:  # network down / outside Yahoo's ~60-day window
        return synthetic_bars(start, end), f"SYNTHETIC fallback (fetch failed: {error})"


def main() -> None:
    symbol = "EURUSD"
    start, end = date(2026, 5, 1), date(2026, 5, 29)
    strategy = MultiTimeframeRsiStrategy()

    bars, source = _load_bars(symbol, start, end)
    result = run_backtest(bars, strategy)

    print(f"Backtest {start} -> {end}  ({symbol}, entry 5m / trend 4h)")
    print(f"  data source:       {source}")
    print(f"  bars (5m closes):  {len(bars)}")
    print(f"  trades:            {result.trades}")
    print(f"  win rate:          {result.win_rate * 100:.1f}%")
    print(f"  total return:      {result.total_return_pct:+.2f}%")
    print(f"  profit factor:     {result.profit_factor:.2f}")
    print(f"  max drawdown:      {result.max_drawdown_pct:.2f}%")


if __name__ == "__main__":
    main()
