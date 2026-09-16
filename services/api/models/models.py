"""
All SQLAlchemy ORM models for MakeMeRich V1.
Tables follow the schema outlined in the system design doc §16.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import enum

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class ExchangeEnum(str, enum.Enum):
    NSE = "NSE"
    BSE = "BSE"


class InstrumentTypeEnum(str, enum.Enum):
    EQ = "EQ"       # Equity
    ETF = "ETF"
    INDEX = "INDEX"


class TimeframeEnum(str, enum.Enum):
    ONE_MIN = "1min"
    FIVE_MIN = "5min"
    FIFTEEN_MIN = "15min"
    THIRTY_MIN = "30min"
    ONE_HOUR = "1hour"
    ONE_DAY = "1day"
    ONE_WEEK = "1week"


class MarketRegimeEnum(str, enum.Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    NEUTRAL = "NEUTRAL"
    SIDEWAYS = "SIDEWAYS"


class CorporateActionTypeEnum(str, enum.Enum):
    SPLIT = "SPLIT"
    BONUS = "BONUS"
    DIVIDEND = "DIVIDEND"
    RIGHTS = "RIGHTS"
    MERGER = "MERGER"
    DEMERGER = "DEMERGER"


# ─────────────────────────────────────────────
# Core / Instrument tables
# ─────────────────────────────────────────────

class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[ExchangeEnum] = mapped_column(Enum(ExchangeEnum), nullable=False)
    instrument_type: Mapped[InstrumentTypeEnum] = mapped_column(Enum(InstrumentTypeEnum), default=InstrumentTypeEnum.EQ)
    isin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    lot_size: Mapped[int] = mapped_column(Integer, default=1)
    tick_size: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0.05"))
    token: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)   # broker-specific token
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("symbol", "exchange", name="uq_instrument_symbol_exchange"),
        Index("ix_instruments_symbol", "symbol"),
        Index("ix_instruments_sector", "sector"),
    )


class MarketCandle(Base):
    """OHLCV time series — will be converted to TimescaleDB hypertable."""
    __tablename__ = "market_candles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("instruments.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[ExchangeEnum] = mapped_column(Enum(ExchangeEnum), nullable=False)
    timeframe: Mapped[TimeframeEnum] = mapped_column(Enum(TimeframeEnum), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    vwap: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    data_source: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "angel_one"

    __table_args__ = (
        UniqueConstraint("symbol", "exchange", "timeframe", "timestamp", name="uq_candle_symbol_tf_ts"),
        Index("ix_candles_symbol_tf_ts", "symbol", "timeframe", "timestamp"),
    )


class MarketQuote(Base):
    """Latest quote snapshot per instrument — updated in real-time."""
    __tablename__ = "market_quotes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[ExchangeEnum] = mapped_column(Enum(ExchangeEnum), nullable=False)
    ltp: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)         # Last Traded Price
    open: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=True)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=True)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=True)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=True)        # prev close
    volume: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    change: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    change_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    data_source: Mapped[str] = mapped_column(String(50), nullable=False)
    quote_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("symbol", "exchange", name="uq_quote_symbol_exchange"),
        Index("ix_quotes_symbol", "symbol"),
    )


class CorporateAction(Base):
    __tablename__ = "corporate_actions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[ExchangeEnum] = mapped_column(Enum(ExchangeEnum), nullable=False)
    action_type: Mapped[CorporateActionTypeEnum] = mapped_column(Enum(CorporateActionTypeEnum), nullable=False)
    ex_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    record_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ratio: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)        # e.g. "2:1" for split
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)  # for dividend
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data_source: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_corp_actions_symbol_date", "symbol", "ex_date"),
    )


# ─────────────────────────────────────────────
# Derived / Feature tables
# ─────────────────────────────────────────────

class TechnicalIndicator(Base):
    """Computed technical indicators per symbol + timeframe + date."""
    __tablename__ = "technical_indicators"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[ExchangeEnum] = mapped_column(Enum(ExchangeEnum), nullable=False)
    timeframe: Mapped[TimeframeEnum] = mapped_column(Enum(TimeframeEnum), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Trend
    ema_9: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    ema_21: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    ema_50: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    ema_200: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    sma_20: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    sma_50: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    sma_200: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))

    # Momentum
    rsi_14: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    macd: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    macd_signal: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    macd_histogram: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))

    # Volatility
    atr_14: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    bb_upper: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    bb_middle: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    bb_lower: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))

    # Trend strength
    adx_14: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))

    # Volume
    volume_ma_20: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    volume_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))  # current / ma_20

    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    model_version: Mapped[str] = mapped_column(String(50), default="feature-v1")

    __table_args__ = (
        UniqueConstraint("symbol", "exchange", "timeframe", "timestamp", name="uq_ti_symbol_tf_ts"),
        Index("ix_ti_symbol_tf_ts", "symbol", "timeframe", "timestamp"),
    )


class MarketRegimeFeature(Base):
    """Daily market-wide regime snapshot (NIFTY + VIX + breadth)."""
    __tablename__ = "market_regime_features"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, unique=True)

    # NIFTY 50
    nifty_close: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    nifty_change_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    nifty_ema_50: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    nifty_ema_200: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))

    # Volatility
    india_vix: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    vix_change_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))

    # Market breadth
    advances: Mapped[Optional[int]] = mapped_column(Integer)
    declines: Mapped[Optional[int]] = mapped_column(Integer)
    unchanged: Mapped[Optional[int]] = mapped_column(Integer)
    advance_decline_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))

    # Computed regime
    regime: Mapped[Optional[MarketRegimeEnum]] = mapped_column(Enum(MarketRegimeEnum))
    regime_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))

    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    model_version: Mapped[str] = mapped_column(String(50), default="regime-v1")

    __table_args__ = (
        Index("ix_regime_date", "date"),
    )


# ─────────────────────────────────────────────
# Fundamentals tables
# ─────────────────────────────────────────────

class FinancialPeriod(Base):
    """Quarterly / Annual financial results per stock."""
    __tablename__ = "financial_periods"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[ExchangeEnum] = mapped_column(Enum(ExchangeEnum), nullable=False)
    period_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "Q" or "A"
    period_label: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "Q1FY26"
    period_end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # P&L
    revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    revenue_yoy_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    gross_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    ebitda: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    ebitda_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    net_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    net_profit_yoy_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    eps: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))

    # Balance sheet
    total_assets: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    total_debt: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    cash_and_equivalents: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))

    # Cash flow
    operating_cash_flow: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    free_cash_flow: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))

    # Returns
    roe: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    roce: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    debt_to_equity: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))

    data_source: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("symbol", "exchange", "period_type", "period_label", name="uq_financials_symbol_period"),
        Index("ix_financials_symbol_date", "symbol", "period_end_date"),
    )


class Fundamental(Base):
    """Latest valuation metrics snapshot per stock."""
    __tablename__ = "fundamentals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[ExchangeEnum] = mapped_column(Enum(ExchangeEnum), nullable=False)
    as_of_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Valuation
    market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(24, 2))
    pe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    pb_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    ev_ebitda: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    dividend_yield: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    face_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    book_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))

    # Shareholding (latest)
    promoter_holding_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    fii_holding_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    dii_holding_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    public_holding_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))

    data_source: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("symbol", "exchange", "as_of_date", name="uq_fundamentals_symbol_date"),
        Index("ix_fundamentals_symbol", "symbol"),
    )


# ─────────────────────────────────────────────
# System / Audit tables
# ─────────────────────────────────────────────

class DataVersion(Base):
    """Track source + version of each data load for reproducibility."""
    __tablename__ = "data_versions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    data_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "market_candles"
    symbol: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    data_source: Mapped[str] = mapped_column(String(50), nullable=False)
    from_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    to_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    records_count: Mapped[Optional[int]] = mapped_column(Integer)
    checksum: Mapped[Optional[str]] = mapped_column(String(64))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """General audit trail for important system actions."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(100))
    entity_id: Mapped[Optional[str]] = mapped_column(String(100))
    details: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
