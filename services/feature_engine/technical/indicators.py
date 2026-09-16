"""
Technical indicator computation using the 'ta' library.
All indicators are computed from OHLCV pandas DataFrames.

Dependencies: ta, pandas, numpy
"""

import logging
from decimal import Decimal
from typing import Optional

import pandas as pd
import ta

logger = logging.getLogger(__name__)


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all technical indicators for a given OHLCV DataFrame.

    Expected input columns: open, high, low, close, volume
    All prices as float.

    Returns the same DataFrame with added indicator columns.
    """
    if len(df) < 30:
        logger.warning("DataFrame too short (%d rows) for reliable indicator computation", len(df))

    close = df["close"].astype(float)
    high  = df["high"].astype(float)
    low   = df["low"].astype(float)
    volume = df["volume"].astype(float)

    # ── Trend: Moving Averages ──────────────────────────────────────────────
    df["ema_9"]   = ta.trend.EMAIndicator(close, window=9).ema_indicator()
    df["ema_21"]  = ta.trend.EMAIndicator(close, window=21).ema_indicator()
    df["ema_50"]  = ta.trend.EMAIndicator(close, window=50).ema_indicator()
    df["ema_200"] = ta.trend.EMAIndicator(close, window=200).ema_indicator()
    df["sma_20"]  = ta.trend.SMAIndicator(close, window=20).sma_indicator()
    df["sma_50"]  = ta.trend.SMAIndicator(close, window=50).sma_indicator()
    df["sma_200"] = ta.trend.SMAIndicator(close, window=200).sma_indicator()

    # ── Momentum: RSI ───────────────────────────────────────────────────────
    df["rsi_14"] = ta.momentum.RSIIndicator(close, window=14).rsi()

    # ── Momentum: MACD ──────────────────────────────────────────────────────
    macd_ind = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    df["macd"]           = macd_ind.macd()
    df["macd_signal"]    = macd_ind.macd_signal()
    df["macd_histogram"] = macd_ind.macd_diff()

    # ── Volatility: ATR ─────────────────────────────────────────────────────
    df["atr_14"] = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()

    # ── Volatility: Bollinger Bands ─────────────────────────────────────────
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    df["bb_upper"]  = bb.bollinger_hband()
    df["bb_middle"] = bb.bollinger_mavg()
    df["bb_lower"]  = bb.bollinger_lband()

    # ── Trend Strength: ADX ─────────────────────────────────────────────────
    df["adx_14"] = ta.trend.ADXIndicator(high, low, close, window=14).adx()

    # ── Volume ──────────────────────────────────────────────────────────────
    df["volume_ma_20"] = volume.rolling(window=20).mean()
    df["volume_ratio"] = volume / df["volume_ma_20"].replace(0, float("nan"))

    return df


def latest_indicators(df: pd.DataFrame) -> dict:
    """
    Returns the most recent row of computed indicators as a dict.
    Converts NaN → None for safe JSON serialization.
    """
    df = compute_all_indicators(df)
    last = df.iloc[-1]

    indicator_cols = [
        "ema_9", "ema_21", "ema_50", "ema_200",
        "sma_20", "sma_50", "sma_200",
        "rsi_14",
        "macd", "macd_signal", "macd_histogram",
        "atr_14",
        "bb_upper", "bb_middle", "bb_lower",
        "adx_14",
        "volume_ma_20", "volume_ratio",
    ]
    result = {}
    for col in indicator_cols:
        val = last.get(col)
        result[col] = None if pd.isna(val) else round(float(val), 4)
    return result
