"""Backtest the multi-timeframe RSI strategy over a historical OHLCV series.

    uv run python src/backtest.py

Walks the entry-timeframe closes bar by bar, reusing the live decision rule
(:meth:`MultiTimeframeRsiStrategy.signal_from_rsi`) with no lookahead — the trend
RSI at each bar comes only from already-completed higher-timeframe blocks. The
position model is *flip on opposite signal*: long until a SELL, short until a BUY
(no pyramiding); the open position is closed at the final bar.

ponytail: cTrader FIX has no history endpoint, so this ships with a deterministic
synthetic price series (`synthetic_closes`). Swap in bars from a real history API
to backtest on actual prices — the engine is unchanged. Results on synthetic data
are illustrative only, not a measure of real performance.
"""

import random
from dataclasses import dataclass
from datetime import date, timedelta

from strategy import MultiTimeframeRsiStrategy, Signal, rsi_series

# 4h trend bar / 5m entry bar = 48 entry bars per trend block.
TREND_RATIO = 48
BARS_PER_DAY = 288  # 24h of 5-minute bars


@dataclass
class BacktestResult:
    trades: int
    wins: int
    win_rate: float
    total_return_pct: float
    profit_factor: float
    max_drawdown_pct: float


def synthetic_closes(
    start: date, end: date, *, seed: int = 20260501, start_price: float = 1.0800
) -> list[float]:
    """Deterministic weekday 5m closes for [start, end] (forex is closed weekends).

    A seeded Gaussian random walk — stands in for a real history feed.
    """
    rng = random.Random(seed)
    closes: list[float] = []
    price = start_price
    day = start
    while day <= end:
        if day.weekday() < 5:  # Mon-Fri
            for _ in range(BARS_PER_DAY):
                price *= 1 + rng.gauss(0, 0.0004)
                closes.append(price)
        day += timedelta(days=1)
    return closes


def run_backtest(
    entry_closes: list[float],
    strategy: MultiTimeframeRsiStrategy,
    trend_ratio: int = TREND_RATIO,
) -> BacktestResult:
    length = strategy.rsi_length
    entry_rsi = rsi_series(entry_closes, length)

    # Trend closes = the close of each completed higher-timeframe block.
    blocks = len(entry_closes) // trend_ratio
    trend_closes = [entry_closes[(b + 1) * trend_ratio - 1] for b in range(blocks)]
    trend_rsi = rsi_series(trend_closes, length) if blocks > length else []

    position = 0  # +1 long, -1 short, 0 flat
    entry_price = 0.0
    returns: list[float] = []

    for index in range(length + 1, len(entry_closes)):
        last_block = index // trend_ratio - 1  # newest fully-completed trend block
        if last_block <= length:
            continue
        signal = strategy.signal_from_rsi(
            trend_rsi[last_block], entry_rsi[index - 1], entry_rsi[index]
        )
        price = entry_closes[index]
        if signal is Signal.BUY and position <= 0:
            if position < 0:
                returns.append((entry_price - price) / entry_price)
            position, entry_price = 1, price
        elif signal is Signal.SELL and position >= 0:
            if position > 0:
                returns.append((price - entry_price) / entry_price)
            position, entry_price = -1, price

    if position != 0:  # close the open position at the last bar
        last = entry_closes[-1]
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


def main() -> None:
    start, end = date(2026, 5, 1), date(2026, 5, 29)
    strategy = MultiTimeframeRsiStrategy()
    closes = synthetic_closes(start, end)
    result = run_backtest(closes, strategy)

    print(f"Backtest {start} -> {end}  (synthetic EURUSD, entry 5m / trend 4h)")
    print(f"  bars (5m closes):  {len(closes)}")
    print(f"  trades:            {result.trades}")
    print(f"  win rate:          {result.win_rate * 100:.1f}%")
    print(f"  total return:      {result.total_return_pct:+.2f}%")
    print(f"  profit factor:     {result.profit_factor:.2f}")
    print(f"  max drawdown:      {result.max_drawdown_pct:.2f}%")


if __name__ == "__main__":
    main()
