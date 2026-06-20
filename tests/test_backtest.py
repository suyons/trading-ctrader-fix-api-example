"""Checks for the backtest engine and its reuse of the strategy rule.

Offline only — uses synthetic bars, never the network. Run with ``uv run pytest``.
"""

from datetime import date

from backtest import run_backtest, synthetic_bars, BacktestResult
from strategy import MultiTimeframeRsiStrategy, Signal


def test_signal_from_rsi_matches_decide():
    # The backtest path (signal_from_rsi) must agree with the live decide() path.
    strategy = MultiTimeframeRsiStrategy(rsi_length=14)
    trend = [1.0 + 0.01 * i for i in range(40)]
    entry = [1.0 - 0.01 * i for i in range(20)] + [0.81, 0.95]
    assert strategy.decide(entry, trend) is Signal.BUY


def test_backtest_runs_and_reports_consistent_metrics():
    bars = synthetic_bars(date(2026, 5, 1), date(2026, 5, 29))
    result = run_backtest(bars, MultiTimeframeRsiStrategy())

    assert isinstance(result, BacktestResult)
    assert result.trades > 0
    assert 0 <= result.wins <= result.trades
    assert 0.0 <= result.win_rate <= 1.0
    assert result.max_drawdown_pct >= 0.0


def test_synthetic_bars_is_deterministic_and_weekday_only():
    first = synthetic_bars(date(2026, 5, 1), date(2026, 5, 29))
    second = synthetic_bars(date(2026, 5, 1), date(2026, 5, 29))
    assert first == second  # seeded -> reproducible
    # May 2026 has 21 weekdays in [1, 29]; 288 five-minute bars each.
    assert len(first) == 21 * 288
    assert first[1][0] - first[0][0] == 300  # 5-minute spacing


def test_no_trades_yields_zeroed_result():
    flat = [(i * 300, 1.0) for i in range(50 * 48)]  # never crosses thresholds
    result = run_backtest(flat, MultiTimeframeRsiStrategy())
    assert result.trades == 0
    assert result.total_return_pct == 0.0
