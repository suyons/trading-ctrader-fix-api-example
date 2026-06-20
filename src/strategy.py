"""Tick-based momentum strategy — FIX-only, no candles, no history.

Consumes the raw bid/ask tick stream from the cTrader FIX quote session and emits
BUY / SELL / HOLD, one tick at a time. This is the kind of strategy FIX is built
for: it reacts to every quote, holds no concept of a "bar", and needs no
historical data — it warms up from the live stream itself.

How it works (all per-tick, on the mid-price):
- a fast and a slow EMA of the mid-price; a crossover is the directional signal,
- an EMA of the spread used as a microstructure guard — signals are suppressed
  when the current spread is wide relative to its recent average (you don't want
  to cross a blown-out spread). A candle/OHLCV strategy can't see this; a tick
  strategy must.

Illustrative, not a production alpha — it shows the FIX tick → decision → execute
loop, not a tuned edge.
"""

from dataclasses import dataclass, field
from enum import Enum


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class TickMomentumStrategy:
    fast_period: int = 20  # in ticks, not bars
    slow_period: int = 100
    spread_period: int = 50
    spread_tolerance: float = 1.5  # act only if spread <= tolerance * average spread

    _fast_ema: float | None = field(default=None, init=False)
    _slow_ema: float | None = field(default=None, init=False)
    _spread_ema: float | None = field(default=None, init=False)
    _ticks: int = field(default=0, init=False)
    _prev_diff: float | None = field(default=None, init=False)

    def __post_init__(self):
        if not 0 < self.fast_period < self.slow_period:
            raise ValueError("require 0 < fast_period < slow_period")
        self._fast_alpha = 2 / (self.fast_period + 1)
        self._slow_alpha = 2 / (self.slow_period + 1)
        self._spread_alpha = 2 / (self.spread_period + 1)

    def update(self, bid: float, ask: float) -> Signal:
        """Feed one tick; return the resulting signal (usually HOLD)."""
        mid = (bid + ask) / 2
        spread = ask - bid

        if self._fast_ema is None:  # seed on the first tick
            self._fast_ema = self._slow_ema = mid
            self._spread_ema = spread
            self._ticks = 1
            return Signal.HOLD

        self._fast_ema += self._fast_alpha * (mid - self._fast_ema)
        self._slow_ema += self._slow_alpha * (mid - self._slow_ema)
        self._spread_ema += self._spread_alpha * (spread - self._spread_ema)
        self._ticks += 1

        diff = self._fast_ema - self._slow_ema  # fast above slow -> positive
        previous = self._prev_diff
        self._prev_diff = diff

        if self._ticks < self.slow_period or previous is None:
            return Signal.HOLD  # still warming up
        crossed_up = previous <= 0 < diff
        crossed_down = previous >= 0 > diff
        if not (crossed_up or crossed_down):
            return Signal.HOLD  # no zero-crossing on this tick
        if spread > self.spread_tolerance * self._spread_ema:
            return Signal.HOLD  # book too wide to act on

        return Signal.BUY if crossed_up else Signal.SELL
