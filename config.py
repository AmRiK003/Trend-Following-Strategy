from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _to_bool(value: str, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    broker_mode: str
    alpaca_api_key: str | None
    alpaca_api_secret: str | None
    alpaca_paper: bool
    symbol: str
    position_size_usd: float
    breakout_lookback: int
    volume_lookback: int
    volume_multiplier: float
    adx_period: int
    adx_min: float
    use_adx_filter: bool
    poll_seconds: int
    data_period: str
    data_interval: str
    paper_starting_cash: float
    paper_state_file: str
    paper_trades_file: str


def load_settings() -> Settings:
    load_dotenv()

    broker_mode = os.getenv("BROKER_MODE", "simulator").strip().lower()
    if broker_mode not in {"simulator", "alpaca"}:
        raise ValueError("BROKER_MODE must be either 'simulator' or 'alpaca'.")

    api_key = os.getenv("ALPACA_API_KEY", "").strip() or None
    api_secret = os.getenv("ALPACA_API_SECRET", "").strip() or None
    if broker_mode == "alpaca" and (not api_key or not api_secret):
        raise ValueError(
            "BROKER_MODE=alpaca requires ALPACA_API_KEY and ALPACA_API_SECRET in .env."
        )

    return Settings(
        broker_mode=broker_mode,
        alpaca_api_key=api_key,
        alpaca_api_secret=api_secret,
        alpaca_paper=_to_bool(os.getenv("ALPACA_PAPER"), default=True),
        symbol=os.getenv("SYMBOL", "AAPL").upper(),
        position_size_usd=float(os.getenv("POSITION_SIZE_USD", "1000")),
        breakout_lookback=int(os.getenv("BREAKOUT_LOOKBACK", "20")),
        volume_lookback=int(os.getenv("VOLUME_LOOKBACK", "20")),
        volume_multiplier=float(os.getenv("VOLUME_MULTIPLIER", "1.5")),
        adx_period=int(os.getenv("ADX_PERIOD", "14")),
        adx_min=float(os.getenv("ADX_MIN", "20")),
        use_adx_filter=_to_bool(os.getenv("USE_ADX_FILTER"), default=True),
        poll_seconds=int(os.getenv("POLL_SECONDS", "900")),
        data_period=os.getenv("DATA_PERIOD", "1y"),
        data_interval=os.getenv("DATA_INTERVAL", "1d"),
        paper_starting_cash=float(os.getenv("PAPER_STARTING_CASH", "100000")),
        paper_state_file=os.getenv("PAPER_STATE_FILE", "paper_state.json"),
        paper_trades_file=os.getenv("PAPER_TRADES_FILE", "paper_trades.csv"),
    )
