"""
Abstract base interface for all market data providers.
All provider adapters must implement this interface.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class CandleData:
    symbol: str
    exchange: str
    timeframe: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    vwap: Optional[Decimal] = None


@dataclass
class QuoteData:
    symbol: str
    exchange: str
    ltp: Decimal
    open: Optional[Decimal]
    high: Optional[Decimal]
    low: Optional[Decimal]
    close: Optional[Decimal]      # previous close
    volume: Optional[int]
    change: Optional[Decimal]
    change_pct: Optional[Decimal]
    quote_timestamp: datetime


@dataclass
class InstrumentData:
    symbol: str
    exchange: str
    name: str
    instrument_type: str
    isin: Optional[str]
    sector: Optional[str]
    token: Optional[str]
    lot_size: int = 1


@dataclass
class CorporateActionData:
    symbol: str
    exchange: str
    action_type: str
    ex_date: datetime
    record_date: Optional[datetime]
    ratio: Optional[str]
    amount: Optional[Decimal]
    remarks: Optional[str]


class MarketDataProvider(ABC):
    """Abstract interface that all market data provider adapters must implement."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique name for this provider e.g. 'angel_one'."""
        ...

    @abstractmethod
    async def get_quote(self, symbol: str, exchange: str = "NSE") -> QuoteData:
        """Fetch latest quote for a symbol."""
        ...

    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        from_date: datetime,
        to_date: datetime,
        exchange: str = "NSE",
    ) -> list[CandleData]:
        """Fetch historical OHLCV candles."""
        ...

    @abstractmethod
    async def get_instrument_master(self, exchange: str = "NSE") -> list[InstrumentData]:
        """Fetch full instrument list for an exchange."""
        ...

    @abstractmethod
    async def get_corporate_actions(
        self, symbol: str, exchange: str = "NSE"
    ) -> list[CorporateActionData]:
        """Fetch corporate actions for a symbol."""
        ...

    async def health_check(self) -> bool:
        """Returns True if the provider API is reachable. Override if needed."""
        try:
            # Attempt a lightweight call
            await self.get_quote("NIFTY", "NSE")
            return True
        except Exception:
            return False
