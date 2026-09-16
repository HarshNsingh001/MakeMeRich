"""
Pydantic response schemas for all API endpoints.
These are the typed contracts between backend and frontend.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


# ─────────────────────────────────────────────
# Instrument / Stock schemas
# ─────────────────────────────────────────────

class InstrumentOut(BaseModel):
    symbol: str
    exchange: str
    name: str
    sector: Optional[str]
    industry: Optional[str]
    instrument_type: str
    isin: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class QuoteOut(BaseModel):
    symbol: str
    exchange: str
    ltp: Decimal
    open: Optional[Decimal]
    high: Optional[Decimal]
    low: Optional[Decimal]
    close: Optional[Decimal]
    volume: Optional[int]
    change: Optional[Decimal]
    change_pct: Optional[Decimal]
    quote_timestamp: datetime

    class Config:
        from_attributes = True


class StockDetailOut(BaseModel):
    instrument: InstrumentOut
    quote: Optional[QuoteOut]


# ─────────────────────────────────────────────
# Market overview schema
# ─────────────────────────────────────────────

class MarketOverviewOut(BaseModel):
    date: datetime
    regime: Optional[str]
    regime_confidence: Optional[Decimal]
    nifty_close: Optional[Decimal]
    nifty_change_pct: Optional[Decimal]
    nifty_ema_50: Optional[Decimal]
    nifty_ema_200: Optional[Decimal]
    india_vix: Optional[Decimal]
    advance_decline_ratio: Optional[Decimal]
    advances: Optional[int]
    declines: Optional[int]


# ─────────────────────────────────────────────
# Technical indicators schema
# ─────────────────────────────────────────────

class TechnicalOut(BaseModel):
    symbol: str
    exchange: str
    timeframe: str
    timestamp: datetime
    ema_9: Optional[Decimal]
    ema_21: Optional[Decimal]
    ema_50: Optional[Decimal]
    ema_200: Optional[Decimal]
    sma_20: Optional[Decimal]
    sma_50: Optional[Decimal]
    sma_200: Optional[Decimal]
    rsi_14: Optional[Decimal]
    macd: Optional[Decimal]
    macd_signal: Optional[Decimal]
    macd_histogram: Optional[Decimal]
    atr_14: Optional[Decimal]
    bb_upper: Optional[Decimal]
    bb_middle: Optional[Decimal]
    bb_lower: Optional[Decimal]
    adx_14: Optional[Decimal]
    volume_ma_20: Optional[Decimal]
    volume_ratio: Optional[Decimal]

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Fundamentals schema
# ─────────────────────────────────────────────

class FundamentalsOut(BaseModel):
    symbol: str
    exchange: str
    as_of_date: datetime
    market_cap: Optional[Decimal]
    pe_ratio: Optional[Decimal]
    pb_ratio: Optional[Decimal]
    ev_ebitda: Optional[Decimal]
    dividend_yield: Optional[Decimal]
    book_value: Optional[Decimal]
    promoter_holding_pct: Optional[Decimal]
    fii_holding_pct: Optional[Decimal]
    dii_holding_pct: Optional[Decimal]

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Candle (chart) schema
# ─────────────────────────────────────────────

class CandleOut(BaseModel):
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    vwap: Optional[Decimal]

    class Config:
        from_attributes = True


class ChartOut(BaseModel):
    symbol: str
    exchange: str
    timeframe: str
    candles: list[CandleOut]


# ─────────────────────────────────────────────
# Paginated stock list
# ─────────────────────────────────────────────

class PaginatedStocksOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[InstrumentOut]
