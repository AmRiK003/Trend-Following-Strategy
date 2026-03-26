from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd


Signal = Literal["BUY", "SELL", "HOLD"]


@dataclass
class StrategyConfig:
    breakout_lookback: int = 20
    volume_lookback: int = 20
    volume_multiplier: float = 1.5
    adx_period: int = 14
    adx_min: float = 20.0
    use_adx_filter: bool = True


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)

    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)) * 100
    return dx.rolling(period).mean()


def add_indicators(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    out = df.copy()
    out["ema_50"] = ema(out["Close"], 50)
    out["ema_200"] = ema(out["Close"], 200)
    out["resistance"] = out["High"].rolling(cfg.breakout_lookback).max().shift(1)
    out["volume_ma"] = out["Volume"].rolling(cfg.volume_lookback).mean()
    out["adx"] = adx(out, cfg.adx_period)
    return out


def generate_signal(df: pd.DataFrame, cfg: StrategyConfig, in_position: bool) -> Signal:
    if len(df) < max(cfg.breakout_lookback + 2, 220):
        return "HOLD"

    ind = add_indicators(df, cfg)
    row = ind.iloc[-1]
    prev = ind.iloc[-2]

    trend_ok = row["ema_50"] > prev["ema_50"] and row["Close"] > row["ema_200"]
    breakout_ok = row["Close"] > row["resistance"]
    volume_ok = row["Volume"] > (row["volume_ma"] * cfg.volume_multiplier)
    adx_ok = (not cfg.use_adx_filter) or (pd.notna(row["adx"]) and row["adx"] >= cfg.adx_min)

    if not in_position and trend_ok and breakout_ok and volume_ok and adx_ok:
        return "BUY"

    if in_position and row["Close"] < row["ema_50"]:
        return "SELL"

    return "HOLD"
