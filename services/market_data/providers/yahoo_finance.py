"""
Yahoo Finance provider adapter — uses yfinance as a secondary/fallback source.

Role in architecture:
  Primary:   Angel One SmartAPI (authenticated, real-time, Indian market native)
  Secondary: Yahoo Finance (unauthenticated, research-grade, global coverage)

Yahoo Finance is suitable for:
  - Historical OHLCV data when Angel One quota is exhausted
  - Fundamental data (PE, PB, market cap, etc.)
  - Corporate actions (dividends, splits)
  - Instrument research

NOT suitable for:
  - Real-time quotes in production (delayed, unofficial)
  - Order execution or routing
  - Backtesting where precise timestamps matter (use Angel One for that)

Source lineage: every record written by this provider sets data_source = "yahoo_finance"
so downstream PiT checks can distinguish provider origin.
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

import yfinance as yf

from providers.base import (
    MarketDataProvider,
    CandleData,
    QuoteData,
    InstrumentData,
    CorporateActionData,
)

logger = logging.getLogger(__name__)

# NSE suffix used by Yahoo Finance
_NSE_SUFFIX = ".NS"
_BSE_SUFFIX = ".BO"


def _yf_ticker(symbol: str, exchange: str) -> str:
    suffix = _NSE_SUFFIX if exchange == "NSE" else _BSE_SUFFIX
    return f"{symbol}{suffix}"


class YahooFinanceProvider(MarketDataProvider):
    """
    Yahoo Finance adapter — implements the MarketDataProvider interface.

    Usage:
        provider = YahooFinanceProvider()
        candles = await provider.get_candles("RELIANCE", "1day", start, end)
    """

    @property
    def provider_name(self) -> str:
        return "yahoo_finance"

    async def get_quote(self, symbol: str, exchange: str = "NSE", **kwargs) -> QuoteData:
        """Fetch latest quote — NOTE: Yahoo quotes are delayed (~15 min) for NSE."""
        ticker = yf.Ticker(_yf_ticker(symbol, exchange))
        info = ticker.fast_info
        now = datetime.utcnow()
        ltp = Decimal(str(info.get("last_price") or info.get("regularMarketPrice") or 0))
        prev_close = Decimal(str(info.get("previous_close") or info.get("regularMarketPreviousClose") or 0))
        return QuoteData(
            symbol=symbol,
            exchange=exchange,
            ltp=ltp,
            open=None,
            high=Decimal(str(info.get("day_high") or 0)) or None,
            low=Decimal(str(info.get("day_low") or 0)) or None,
            close=prev_close,
            volume=int(info.get("three_month_average_volume") or 0) or None,
            change=ltp - prev_close if ltp and prev_close else None,
            change_pct=None,
            quote_timestamp=now,
        )

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        from_date: datetime,
        to_date: datetime,
        exchange: str = "NSE",
        **kwargs,
    ) -> list[CandleData]:
        """Fetch historical OHLCV candles from Yahoo Finance."""
        interval_map = {
            "1min": "1m", "5min": "5m", "15min": "15m", "30min": "30m",
            "1hour": "1h", "1day": "1d", "1week": "1wk",
        }
        interval = interval_map.get(timeframe, "1d")
        ticker = yf.Ticker(_yf_ticker(symbol, exchange))
        df = ticker.history(
            start=from_date.strftime("%Y-%m-%d"),
            end=to_date.strftime("%Y-%m-%d"),
            interval=interval,
            auto_adjust=True,
        )

        candles = []
        for ts, row in df.iterrows():
            # yfinance returns timezone-aware timestamps
            ts_dt = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else datetime.utcfromtimestamp(ts.timestamp())
            candles.append(CandleData(
                symbol=symbol,
                exchange=exchange,
                timeframe=timeframe,
                timestamp=ts_dt,
                open=Decimal(str(round(row["Open"], 4))),
                high=Decimal(str(round(row["High"], 4))),
                low=Decimal(str(round(row["Low"], 4))),
                close=Decimal(str(round(row["Close"], 4))),
                volume=int(row.get("Volume", 0)),
            ))
        logger.info(f"YahooFinance: {len(candles)} candles for {symbol} ({from_date.date()} → {to_date.date()})")
        return candles

    async def get_instrument_master(self, exchange: str = "NSE") -> list[InstrumentData]:
        """
        Yahoo Finance does not provide a universe listing endpoint.
        Returns empty list — use Angel One for instrument master ingestion.
        """
        logger.warning("YahooFinance: get_instrument_master() not supported; use AngelOneProvider.")
        return []

    async def get_corporate_actions(
        self, symbol: str, exchange: str = "NSE"
    ) -> list[CorporateActionData]:
        """
        Fetch splits and dividends from Yahoo Finance.
        Returns both splits and dividends as CorporateActionData.
        """
        ticker = yf.Ticker(_yf_ticker(symbol, exchange))
        actions = []

        # Dividends
        try:
            dividends = ticker.dividends
            for ts, amount in dividends.items():
                ts_dt = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else datetime.utcfromtimestamp(ts.timestamp())
                actions.append(CorporateActionData(
                    symbol=symbol,
                    exchange=exchange,
                    action_type="DIVIDEND",
                    ex_date=ts_dt,
                    record_date=None,
                    ratio=None,
                    amount=Decimal(str(round(float(amount), 4))),
                    remarks=f"Dividend ₹{amount:.2f}",
                ))
        except Exception as e:
            logger.warning(f"YahooFinance: could not fetch dividends for {symbol}: {e}")

        # Splits
        try:
            splits = ticker.splits
            for ts, ratio in splits.items():
                ts_dt = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else datetime.utcfromtimestamp(ts.timestamp())
                # ratio e.g. 2.0 means 2:1 split
                ratio_str = f"{int(ratio)}:1" if ratio == int(ratio) else str(ratio)
                actions.append(CorporateActionData(
                    symbol=symbol,
                    exchange=exchange,
                    action_type="SPLIT",
                    ex_date=ts_dt,
                    record_date=None,
                    ratio=ratio_str,
                    amount=None,
                    remarks=f"Stock split {ratio_str}",
                ))
        except Exception as e:
            logger.warning(f"YahooFinance: could not fetch splits for {symbol}: {e}")

        return actions

    async def get_fundamentals(self, symbol: str, exchange: str = "NSE") -> dict:
        """
        Fetch fundamental data from Yahoo Finance.
        Returns a dict of valuation metrics.
        NOTE: This is a Yahoo-specific extension — not in the base interface.
        Use for research/fallback. Always tag results as source='yahoo_finance'.
        """
        try:
            ticker = yf.Ticker(_yf_ticker(symbol, exchange))
            info = ticker.info
            return {
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "ev_ebitda": info.get("enterpriseToEbitda"),
                "dividend_yield": info.get("dividendYield"),
                "roe": info.get("returnOnEquity"),
                "revenue": info.get("totalRevenue"),
                "net_profit": info.get("netIncomeToCommon"),
                "eps": info.get("trailingEps"),
                "debt_to_equity": info.get("debtToEquity"),
                "book_value": info.get("bookValue"),
                "source": "yahoo_finance",
                "retrieved_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"YahooFinance: could not fetch fundamentals for {symbol}: {e}")
            return {}

    async def health_check(self) -> bool:
        """Check if Yahoo Finance is reachable by fetching NIFTY 50 info."""
        try:
            ticker = yf.Ticker("^NSEI")
            info = ticker.fast_info
            return bool(info)
        except Exception:
            return False
