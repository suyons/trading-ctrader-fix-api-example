"""Multi-timeframe RSI strategy (the decision engine described in the README).

Mirrors the TradingView "Multi Timeframe RSI" indicator this project grew from:

    BUY  when RSI(trend timeframe) > midline   AND RSI(entry tf) crosses up   oversold
    SELL when RSI(trend timeframe) < midline   AND RSI(entry tf) crosses down overbought

The higher (trend) timeframe classifies the trend; the entry timeframe spots the
oversold/overbought turn. RSI uses Wilder's smoothing, matching TradingView's
``ta.rsi`` so signals line up with the chart in ``docs/``.
"""

from dataclasses import dataclass
from enum import Enum


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


def rsi_series(closes: list[float], length: int) -> list[float]:
    """Wilder's RSI for each close, aligned to ``closes`` (oldest -> newest).

    The first ``length`` entries are ``None`` (not enough data to seed the
    average), matching how ``ta.rsi`` only emits values once warmed up.
    """
    if length < 1:
        raise ValueError("RSI length must be >= 1")
    if len(closes) <= length:
        raise ValueError(
            f"need more than {length} closes to compute RSI, got {len(closes)}"
        )

    gains = 0.0
    losses = 0.0
    for index in range(1, length + 1):
        change = closes[index] - closes[index - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    avg_gain = gains / length
    avg_loss = losses / length

    result: list[float | None] = [None] * length
    result.append(_rsi_from_averages(avg_gain, avg_loss))

    for index in range(length + 1, len(closes)):
        change = closes[index] - closes[index - 1]
        avg_gain = (avg_gain * (length - 1) + max(change, 0.0)) / length
        avg_loss = (avg_loss * (length - 1) + max(-change, 0.0)) / length
        result.append(_rsi_from_averages(avg_gain, avg_loss))

    return result


def _rsi_from_averages(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0.0:
        return 100.0
    relative_strength = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


@dataclass(frozen=True)
class MultiTimeframeRsiStrategy:
    rsi_length: int = 21
    oversold: float = 40.0
    midline: float = 50.0
    overbought: float = 60.0

    def decide(
        self, entry_closes: list[float], trend_closes: list[float]
    ) -> Signal:
        """Return BUY / SELL / HOLD from entry- and trend-timeframe closes.

        ``entry_closes``  -- closes on the fast entry timeframe (e.g. 5m).
        ``trend_closes``  -- closes on the higher trend timeframe (e.g. 240m).
        Both oldest -> newest.
        """
        entry_rsi = rsi_series(entry_closes, self.rsi_length)
        trend_rsi = rsi_series(trend_closes, self.rsi_length)[-1]

        previous, current = entry_rsi[-2], entry_rsi[-1]
        if previous is None:
            raise ValueError("need at least one more entry close for a crossover")

        return self.signal_from_rsi(trend_rsi, previous, current)

    def signal_from_rsi(
        self, trend_rsi: float, previous_entry_rsi: float, current_entry_rsi: float
    ) -> Signal:
        """The core rule, on already-computed RSI values (reused by the backtest)."""
        crossed_up = previous_entry_rsi <= self.oversold < current_entry_rsi
        crossed_down = previous_entry_rsi >= self.overbought > current_entry_rsi

        if trend_rsi > self.midline and crossed_up:
            return Signal.BUY
        if trend_rsi < self.midline and crossed_down:
            return Signal.SELL
        return Signal.HOLD
