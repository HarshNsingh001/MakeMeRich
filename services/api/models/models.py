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
    Integer, JSON, Numeric, String, Text, UniqueConstraint, Index
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


class AlertConditionEnum(str, enum.Enum):
    PRICE_ABOVE = "PRICE_ABOVE"
    PRICE_BELOW = "PRICE_BELOW"
    RSI_ABOVE = "RSI_ABOVE"
    RSI_BELOW = "RSI_BELOW"
    OPPORTUNITY_HIGH = "OPPORTUNITY_HIGH"
    OPPORTUNITY_MODERATE = "OPPORTUNITY_MODERATE"


# ─────────────────────────────────────────────
# Users & Auth
# ─────────────────────────────────────────────

class User(Base):
    """Registered platform user."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # Profile / Risk
    risk_profile: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # CONSERVATIVE | MODERATE | AGGRESSIVE
    investment_horizon: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # SHORT | MEDIUM | LONG

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_users_email", "email"),
    )


# ─────────────────────────────────────────────
# Watchlists
# ─────────────────────────────────────────────

class Watchlist(Base):
    """Named watchlist owned by a user."""
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_watchlists_user_id", "user_id"),
    )


class WatchlistItem(Base):
    """Single stock entry inside a watchlist."""
    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    watchlist_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("watchlists.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[ExchangeEnum] = mapped_column(Enum(ExchangeEnum), default=ExchangeEnum.NSE)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("watchlist_id", "symbol", "exchange", name="uq_watchlist_item"),
        Index("ix_watchlist_items_watchlist_id", "watchlist_id"),
    )


# ─────────────────────────────────────────────
# Alerts & Notifications
# ─────────────────────────────────────────────

class Alert(Base):
    """User-defined price/indicator alert for a stock."""
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[ExchangeEnum] = mapped_column(Enum(ExchangeEnum), default=ExchangeEnum.NSE)
    condition: Mapped[AlertConditionEnum] = mapped_column(Enum(AlertConditionEnum), nullable=False)
    threshold_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_alerts_user_symbol", "user_id", "symbol"),
    )


class Notification(Base):
    """In-app notification delivered to a user."""
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    related_symbol: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_notifications_user_id", "user_id"),
    )





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
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

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
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

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


class RecommendationSnapshot(Base):
    """Stores the full auditable decision from the multi-agent AI engine."""
    __tablename__ = "recommendation_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[ExchangeEnum] = mapped_column(Enum(ExchangeEnum), default=ExchangeEnum.NSE)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Context known at decision time
    current_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    
    # LangGraph Output
    opportunity_level: Mapped[str] = mapped_column(String(20), nullable=False) # LOW | MODERATE | HIGH
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)        # LOW | MEDIUM | HIGH
    time_horizon: Mapped[str] = mapped_column(String(50), nullable=False)      
    
    # Store full JSON output
    opportunity_state_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    agent_evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    critic_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    model_version: Mapped[str] = mapped_column(String(50), default="decision-v2-agents")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        Index("ix_recommendations_symbol_date", "symbol", "timestamp"),
    )


# ─────────────────────────────────────────────
# Historical Evaluation / Backtest tables
# ─────────────────────────────────────────────

class BacktestExecution(Base):
    __tablename__ = "backtest_executions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="QUEUED")
    pipeline_version: Mapped[str] = mapped_column(String(50))
    model_version: Mapped[str] = mapped_column(String(50))
    prompt_version: Mapped[str] = mapped_column(String(50))
    feature_version: Mapped[str] = mapped_column(String(50))
    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    completed_cases: Mapped[int] = mapped_column(Integer, default=0)
    failed_cases: Mapped[int] = mapped_column(Integer, default=0)
    llm_budget: Mapped[int] = mapped_column(Integer, default=0)
    llm_calls_used: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

class BacktestCase(Base):
    __tablename__ = "backtest_cases"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String(50), ForeignKey("backtest_executions.execution_id"))
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    target_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="QUEUED")
    retries: Mapped[int] = mapped_column(Integer, default=0)
    input_snapshot_hash: Mapped[Optional[str]] = mapped_column(String(64))
    feature_snapshot_hash: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class BacktestResult(Base):
    __tablename__ = "backtest_results"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("backtest_cases.id"))
    execution_id: Mapped[str] = mapped_column(String(50), ForeignKey("backtest_executions.execution_id"))
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    target_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Return metrics
    gross_return_t5: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    gross_return_t10: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    gross_return_t20: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    net_return_t5: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    net_return_t10: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    net_return_t20: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    nifty_return_t5: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    nifty_return_t10: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    nifty_return_t20: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    relative_return_t5: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    relative_return_t10: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    relative_return_t20: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    
    # Risk
    mae: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    mfe: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    
    # AI Output
    opportunity_level: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    structured_evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────────────────────────────
# 12 New Advanced Feature & Audit Tables (V1.5)
# ─────────────────────────────────────────────

class SectorClassification(Base):
    __tablename__ = "sector_classifications"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[ExchangeEnum] = mapped_column(Enum(ExchangeEnum), default=ExchangeEnum.NSE)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    industry: Mapped[str] = mapped_column(String(100), nullable=False)
    basic_industry: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_sector_class_symbol", "symbol"),)


class ValuationFeature(Base):
    __tablename__ = "valuation_features"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[ExchangeEnum] = mapped_column(Enum(ExchangeEnum), default=ExchangeEnum.NSE)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    peg_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    earnings_yield: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    fcf_yield: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    sector_pe_percentile: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    sector_pb_percentile: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (Index("ix_val_feat_symbol_ts", "symbol", "timestamp"),)


class RelativeStrengthFeature(Base):
    __tablename__ = "relative_strength_features"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[ExchangeEnum] = mapped_column(Enum(ExchangeEnum), default=ExchangeEnum.NSE)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    rs_vs_nifty_5d: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    rs_vs_nifty_20d: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    rs_vs_nifty_60d: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    rs_vs_sector_20d: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketDepthSnapshot(Base):
    __tablename__ = "market_depth_snapshots"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[ExchangeEnum] = mapped_column(Enum(ExchangeEnum), default=ExchangeEnum.NSE)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    total_buy_qty: Mapped[Optional[int]] = mapped_column(BigInteger)
    total_sell_qty: Mapped[Optional[int]] = mapped_column(BigInteger)
    bid_ask_spread: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    depth_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    __table_args__ = (Index("ix_market_depth_symbol_ts", "symbol", "timestamp"),)


class ShareholdingPattern(Base):
    __tablename__ = "shareholding_patterns"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[ExchangeEnum] = mapped_column(Enum(ExchangeEnum), default=ExchangeEnum.NSE)
    as_of_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    promoter_holding_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    fii_holding_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    dii_holding_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    public_holding_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    mutual_fund_holding_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    pledged_promoter_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    
    __table_args__ = (Index("ix_shareholding_symbol_date", "symbol", "as_of_date"),)


class ModelVersionRegistry(Base):
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    version_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "langgraph_agent"
    provider_model: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. "llama3-70b-8192"
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    recommendation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("recommendation_snapshots.id"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version_id: Mapped[str] = mapped_column(String(50), ForeignKey("model_versions.version_id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    tokens_prompt: Mapped[Optional[int]] = mapped_column(Integer)
    tokens_completion: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS") # SUCCESS, FAILED
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    raw_response: Mapped[dict] = mapped_column(JSON)


class AgentClaim(Base):
    __tablename__ = "agent_claims"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    agent_run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agent_runs.id"), nullable=False)
    claim_type: Mapped[str] = mapped_column(String(50), nullable=False) # THESIS, SUPPORTING, CONTRADICTORY, INVALIDATION
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentEvidence(Base):
    __tablename__ = "agent_evidence"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    agent_claim_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agent_claims.id"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[str] = mapped_column(String(255), nullable=False)
    data_source_id: Mapped[Optional[str]] = mapped_column(String(100)) # ID of the DB record this came from


class CriticRun(Base):
    __tablename__ = "critic_runs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    recommendation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("recommendation_snapshots.id"), nullable=False)
    verdict: Mapped[str] = mapped_column(String(20), nullable=False) # PASS, FAIL, MODIFY
    feedback_text: Mapped[Text] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserPortfolio(Base):
    __tablename__ = "portfolios"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[ExchangeEnum] = mapped_column(Enum(ExchangeEnum), default=ExchangeEnum.NSE)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    average_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint("user_id", "symbol", "exchange", name="uq_portfolio_item"),)


class RecommendationOutcome(Base):
    __tablename__ = "recommendation_outcomes"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    recommendation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("recommendation_snapshots.id"), nullable=False)
    target_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluation_type: Mapped[str] = mapped_column(String(20), nullable=False) # T+5, T+20
    
    price_at_recommendation: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    price_at_target: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    highest_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    lowest_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    
    hit_invalidation: Mapped[bool] = mapped_column(Boolean, default=False)
    hit_target: Mapped[bool] = mapped_column(Boolean, default=False)
    net_return_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    nifty_return_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
