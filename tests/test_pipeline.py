"""Wiring check: the sample data source feeds the strategy and yields a Signal.

Run with ``uv run pytest``.
"""

from main import HISTORY, decide_signal
from market_data import SampleMarketData
from strategy import Signal


def test_sample_provider_returns_requested_count():
    closes = SampleMarketData().fetch_closes("EURUSD", "5m", HISTORY)
    assert len(closes) == HISTORY


def test_pipeline_yields_a_signal():
    assert isinstance(decide_signal(SampleMarketData()), Signal)
