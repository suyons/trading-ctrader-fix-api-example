"""Check the FIX tick stream helper: subscribes, dedupes, yields new ticks.

Offline — a fake client stands in for the FIX quote session. Run with pytest.
"""

import itertools

from main import stream_ticks


class FakeClient:
    """Minimal stand-in for Ctrader: records subscribe, replays quotes."""

    def __init__(self, quotes):
        self._quotes = list(quotes)
        self.subscribed = []

    def subscribe(self, symbol):
        self.subscribed.append(symbol)

    def quote(self, symbol):
        # Return the next quote, then keep repeating the last (no new tick).
        if len(self._quotes) > 1:
            return self._quotes.pop(0)
        return self._quotes[0]


def test_stream_subscribes_and_yields_distinct_ticks():
    quotes = [
        {"time": 1, "bid": 1.1000, "ask": 1.1001},
        {"time": 2, "bid": 1.1002, "ask": 1.1003},  # duplicate sent twice below
        {"time": 2, "bid": 1.1002, "ask": 1.1003},
        {"time": 3, "bid": 1.1004, "ask": 1.1005},
    ]
    client = FakeClient(quotes)
    stream = stream_ticks(client, "EURUSD", poll_interval=0.0)

    ticks = list(itertools.islice(stream, 3))

    assert client.subscribed == ["EURUSD"]
    assert ticks == [(1.1000, 1.1001), (1.1002, 1.1003), (1.1004, 1.1005)]
