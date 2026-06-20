"""Fetch real historical OHLCV bars from Yahoo Finance (no API key, stdlib only).

cTrader FIX has no history endpoint, so the backtest sources real prices here.
Yahoo keeps intraday data (e.g. 5m) for only ~60 days, so windows older than that
fall out of range and the fetch fails — the backtest then falls back to synthetic
data. Returns bars as ``(epoch_seconds_utc, close)``.
"""

import json
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/"
_SYMBOLS = {"EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "XAUUSD": "XAUUSD=X"}
_INTERVALS = {"5m": "5m", "15m": "15m", "1h": "60m", "1d": "1d"}


def fetch_bars(
    symbol: str, interval: str, start: date, end: date, *, timeout: float = 30
) -> list[tuple[int, float]]:
    """Return ``[(epoch_seconds, close)]`` for ``[start, end]`` (end inclusive), UTC.

    Yahoo ignores ``period2`` for intraday and returns its whole retained window,
    so we filter to the requested range ourselves.
    """
    yahoo_symbol = _SYMBOLS.get(symbol, symbol)
    yahoo_interval = _INTERVALS.get(interval, interval)
    start_ts = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())
    end_ts = int(
        (datetime(end.year, end.month, end.day, tzinfo=timezone.utc) + timedelta(days=1)).timestamp()
    )

    query = urllib.parse.urlencode(
        {"period1": start_ts, "period2": end_ts, "interval": yahoo_interval}
    )
    request = urllib.request.Request(
        f"{_CHART_URL}{urllib.parse.quote(yahoo_symbol)}?{query}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)

    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    closes = result["indicators"]["quote"][0].get("close") or []
    bars = [
        (ts, close)
        for ts, close in zip(timestamps, closes)
        if close is not None and start_ts <= ts < end_ts
    ]
    if not bars:
        raise ValueError(f"no {interval} bars returned for {symbol} in the window")
    return bars
