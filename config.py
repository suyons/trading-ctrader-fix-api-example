"""Load cTrader FIX API credentials from the environment / a local .env file.

Credentials never live in source. Copy ``.env.example`` to ``.env`` and fill it
in; :func:`load_config` reads it and fails fast if anything required is missing.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _env_flag(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class CtraderConfig:
    host: str
    sender_comp_id: str  # full account string, e.g. "demo.yourbroker.1234567"
    password: str
    currency: str = "USD"
    use_ssl: bool = True  # True -> TLS ports 5211/5212, False -> plain 5201/5202


def load_config() -> CtraderConfig:
    load_dotenv()
    try:
        return CtraderConfig(
            host=os.environ["CTRADER_HOST"],
            sender_comp_id=os.environ["CTRADER_SENDER_COMP_ID"],
            password=os.environ["CTRADER_PASSWORD"],
            currency=os.environ.get("CTRADER_CURRENCY", "USD"),
            use_ssl=_env_flag("CTRADER_USE_SSL", True),
        )
    except KeyError as missing:
        raise RuntimeError(
            f"Missing required environment variable {missing}. "
            "Copy .env.example to .env and fill in your cTrader FIX credentials."
        ) from None
