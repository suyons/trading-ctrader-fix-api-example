"""cTrader FIX API example package.

Public surface:
    Ctrader                     -- high-level trading client (FIX 4.4)
    MultiTimeframeRsiStrategy   -- the multi-timeframe RSI decision engine
    Signal                      -- BUY / SELL / HOLD
    load_config                 -- read credentials from environment / .env
"""

from .ctrader_client import Ctrader
from .strategy import MultiTimeframeRsiStrategy, Signal
from .config import load_config, CtraderConfig

__all__ = [
    "Ctrader",
    "MultiTimeframeRsiStrategy",
    "Signal",
    "load_config",
    "CtraderConfig",
]
