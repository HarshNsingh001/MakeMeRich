"""
Market Regime computation.
Determines overall Indian market state: BULL / BEAR / NEUTRAL / SIDEWAYS

Inputs:
  - NIFTY 50 daily candles
  - India VIX daily values
  - NSE advance/decline data

Output: MarketRegimeEnum + confidence score
"""

import logging
from decimal import Decimal
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def compute_regime(
    nifty_df: pd.DataFrame,
    vix_df: Optional[pd.DataFrame] = None,
    advances: Optional[int] = None,
    declines: Optional[int] = None,
) -> dict:
    """
    Compute market regime from NIFTY price data and optionally VIX + breadth.

    Args:
        nifty_df: DataFrame with 'close' column (NIFTY daily candles, sorted ascending)
        vix_df:   DataFrame with 'close' column (India VIX daily)
        advances: Number of advancing stocks today
        declines: Number of declining stocks today

    Returns dict with:
        regime: BULL | BEAR | NEUTRAL | SIDEWAYS
        confidence: 0..1
        nifty_close: latest NIFTY close
        nifty_ema_50: 50-day EMA
        nifty_ema_200: 200-day EMA
        india_vix: latest VIX value
        advance_decline_ratio: advances / declines
    """
    result: dict = {
        "regime": "NEUTRAL",
        "confidence": 0.5,
        "nifty_close": None,
        "nifty_change_pct": None,
        "nifty_ema_50": None,
        "nifty_ema_200": None,
        "india_vix": None,
        "advance_decline_ratio": None,
    }

    if nifty_df is None or len(nifty_df) < 10:
        logger.warning("Insufficient NIFTY data for regime computation")
        return result

    close = nifty_df["close"].astype(float)
    latest_close = close.iloc[-1]
    prev_close = close.iloc[-2] if len(close) >= 2 else latest_close

    result["nifty_close"] = round(latest_close, 2)
    result["nifty_change_pct"] = round((latest_close - prev_close) / prev_close * 100, 4)

    # Moving averages
    ema_50  = close.ewm(span=50, adjust=False).mean().iloc[-1] if len(close) >= 50 else None
    ema_200 = close.ewm(span=200, adjust=False).mean().iloc[-1] if len(close) >= 200 else None
    result["nifty_ema_50"]  = round(ema_50, 2) if ema_50 else None
    result["nifty_ema_200"] = round(ema_200, 2) if ema_200 else None

    # VIX
    if vix_df is not None and len(vix_df) > 0:
        vix_close = float(vix_df["close"].iloc[-1])
        result["india_vix"] = round(vix_close, 2)
    else:
        vix_close = None

    # Advance / decline ratio
    if advances and declines and declines > 0:
        adr = advances / declines
        result["advance_decline_ratio"] = round(adr, 4)
    else:
        adr = None

    # ── Regime logic ──────────────────────────────────────────────────────
    # Simple rule-based regime (can be replaced by ML model in V2)
    bull_signals = 0
    bear_signals = 0
    total_signals = 0

    if ema_50 and ema_200:
        total_signals += 1
        if latest_close > ema_50 > ema_200:
            bull_signals += 1          # price above both MAs: bullish
        elif latest_close < ema_50 < ema_200:
            bear_signals += 1          # price below both MAs: bearish

    if ema_50:
        total_signals += 1
        if latest_close > ema_50:
            bull_signals += 1
        else:
            bear_signals += 1

    if vix_close is not None:
        total_signals += 1
        if vix_close < 15:
            bull_signals += 1          # low fear = bullish
        elif vix_close > 25:
            bear_signals += 1          # high fear = bearish

    if adr is not None:
        total_signals += 1
        if adr > 1.5:
            bull_signals += 1          # more advances than declines
        elif adr < 0.7:
            bear_signals += 1

    if total_signals == 0:
        return result

    bull_ratio = bull_signals / total_signals
    bear_ratio = bear_signals / total_signals

    if bull_ratio >= 0.6:
        result["regime"] = "BULL"
        result["confidence"] = round(bull_ratio, 4)
    elif bear_ratio >= 0.6:
        result["regime"] = "BEAR"
        result["confidence"] = round(bear_ratio, 4)
    elif abs(bull_ratio - bear_ratio) < 0.2:
        result["regime"] = "SIDEWAYS"
        result["confidence"] = round(0.5 + abs(bull_ratio - bear_ratio), 4)
    else:
        result["regime"] = "NEUTRAL"
        result["confidence"] = 0.5

    return result
