"""
Fundamental Data Ingestion Service
Uses yfinance (Yahoo Finance) to fetch PE, ROE, D/E, market cap, etc.
for all NSE-listed stocks in the instruments table.

Run: python -m services.fundamental_ingestor
Or:  python services/fundamental_ingestor.py
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

import yfinance as yf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.database import AsyncSessionLocal
from models.models import Instrument, Fundamental, ExchangeEnum

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def to_decimal(val, scale: int = 4) -> Optional[Decimal]:
    """Safely convert a value to Decimal, return None on failure."""
    if val is None:
        return None
    try:
        return round(Decimal(str(val)), scale)
    except (InvalidOperation, ValueError, TypeError):
        return None


def fetch_fundamentals_from_yf(symbol: str, exchange: str) -> Optional[dict]:
    """
    Fetch fundamental metrics from Yahoo Finance.
    NSE symbols are suffixed with .NS, BSE with .BO
    """
    suffix = ".NS" if exchange == "NSE" else ".BO"
    ticker_symbol = f"{symbol}{suffix}"
    
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        # If Yahoo doesn't know this symbol, info will have very few keys
        if len(info) < 10 or info.get("quoteType") is None:
            return None
        
        return {
            "symbol": symbol,
            "exchange": exchange,
            "as_of_date": datetime.now(timezone.utc),
            # Valuation
            "market_cap": to_decimal(info.get("marketCap"), 2),
            "pe_ratio": to_decimal(info.get("trailingPE")),
            "pb_ratio": to_decimal(info.get("priceToBook")),
            "ev_ebitda": to_decimal(info.get("enterpriseToEbitda")),
            "dividend_yield": to_decimal(info.get("dividendYield")),
            "face_value": to_decimal(info.get("faceValue")),
            "book_value": to_decimal(info.get("bookValue")),
            # Shareholding (Yahoo provides insider/institutional as proxy)
            "promoter_holding_pct": to_decimal(info.get("heldPercentInsiders")),
            "fii_holding_pct": to_decimal(info.get("heldPercentInstitutions")),
            "dii_holding_pct": None,     # Not available from Yahoo
            "public_holding_pct": None,   # Not available from Yahoo
            # Enrichment: also update sector/industry on the Instrument
            "sector": info.get("sector") or info.get("sectorDisp"),
            "industry": info.get("industry") or info.get("industryDisp"),
            "data_source": "yahoo_finance",
        }
    except Exception as e:
        logger.debug(f"Failed to fetch {ticker_symbol}: {e}")
        return None


async def upsert_fundamental(db: AsyncSession, data: dict) -> bool:
    """Insert or update a Fundamental record (upsert by symbol+exchange+date)."""
    try:
        # Upsert into fundamentals
        stmt = pg_insert(Fundamental.__table__).values(
            symbol=data["symbol"],
            exchange=data["exchange"],
            as_of_date=data["as_of_date"],
            market_cap=data["market_cap"],
            pe_ratio=data["pe_ratio"],
            pb_ratio=data["pb_ratio"],
            ev_ebitda=data["ev_ebitda"],
            dividend_yield=data["dividend_yield"],
            face_value=data["face_value"],
            book_value=data["book_value"],
            promoter_holding_pct=data["promoter_holding_pct"],
            fii_holding_pct=data["fii_holding_pct"],
            dii_holding_pct=data["dii_holding_pct"],
            public_holding_pct=data["public_holding_pct"],
            data_source=data["data_source"],
        ).on_conflict_do_update(
            constraint="uq_fundamentals_symbol_date",
            set_={
                "market_cap": data["market_cap"],
                "pe_ratio": data["pe_ratio"],
                "pb_ratio": data["pb_ratio"],
                "ev_ebitda": data["ev_ebitda"],
                "dividend_yield": data["dividend_yield"],
                "face_value": data["face_value"],
                "book_value": data["book_value"],
                "promoter_holding_pct": data["promoter_holding_pct"],
                "fii_holding_pct": data["fii_holding_pct"],
                "data_source": data["data_source"],
            }
        )
        await db.execute(stmt)

        # Also enrich sector/industry on Instrument if missing
        if data.get("sector") or data.get("industry"):
            inst_stmt = select(Instrument).where(
                Instrument.symbol == data["symbol"],
                Instrument.exchange == ExchangeEnum(data["exchange"])
            ).limit(1)
            result = await db.execute(inst_stmt)
            inst = result.scalar_one_or_none()
            if inst:
                if not inst.sector and data.get("sector"):
                    inst.sector = data["sector"]
                if not inst.industry and data.get("industry"):
                    inst.industry = data["industry"]

        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"DB error upserting {data['symbol']}: {e}")
        return False


async def run_ingestion(
    limit: Optional[int] = None,
    delay_seconds: float = 0.5,
    exchange_filter: str = "NSE"
):
    """
    Main ingestion loop.
    
    Args:
        limit: Max number of stocks to process (None = all)
        delay_seconds: Pause between Yahoo API calls to avoid rate-limiting
        exchange_filter: 'NSE' or 'BSE'
    """
    logger.info("="*60)
    logger.info("  Fundamental Data Ingestion — Yahoo Finance")
    logger.info("="*60)

    async with AsyncSessionLocal() as db:
        # Fetch all active instruments from DB
        stmt = select(Instrument).where(
            Instrument.is_active == True,
            Instrument.exchange == ExchangeEnum(exchange_filter)
        ).order_by(Instrument.symbol)

        if limit:
            stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        instruments = result.scalars().all()

    total = len(instruments)
    logger.info(f"Found {total} instruments to process.\n")

    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, inst in enumerate(instruments, 1):
        symbol = inst.symbol
        exchange = inst.exchange.value

        logger.info(f"[{i}/{total}] Processing {symbol}...")

        # Fetch from Yahoo Finance (synchronous call in thread)
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, fetch_fundamentals_from_yf, symbol, exchange
        )

        if data is None:
            logger.warning(f"  ↳ Skipped — not found on Yahoo Finance")
            skip_count += 1
        else:
            # Save to DB
            async with AsyncSessionLocal() as db:
                saved = await upsert_fundamental(db, data)
            if saved:
                pe_str = f"PE={data['pe_ratio']}" if data['pe_ratio'] else "PE=N/A"
                pb_str = f"PB={data['pb_ratio']}" if data['pb_ratio'] else "PB=N/A"
                logger.info(f"  ↳ ✅ Saved | {pe_str} | {pb_str} | MCap={data['market_cap']}")
                success_count += 1
            else:
                fail_count += 1

        # Rate-limit guard
        time.sleep(delay_seconds)

        # Progress report every 50 stocks
        if i % 50 == 0:
            logger.info(f"\n--- Progress: {i}/{total} | ✅ {success_count} | ⚠ {skip_count} | ❌ {fail_count} ---\n")

    logger.info("\n" + "="*60)
    logger.info("  INGESTION COMPLETE")
    logger.info("="*60)
    logger.info(f"  Total processed : {total}")
    logger.info(f"  ✅ Saved         : {success_count}")
    logger.info(f"  ⚠  Skipped       : {skip_count} (not on Yahoo Finance)")
    logger.info(f"  ❌ Failed        : {fail_count}")
    logger.info("="*60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fundamental Data Ingestion via Yahoo Finance")
    parser.add_argument("--limit", type=int, default=None, help="Limit to N stocks (default: all)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between API calls in seconds (default: 0.5)")
    parser.add_argument("--exchange", type=str, default="NSE", choices=["NSE", "BSE"], help="Exchange to process")
    args = parser.parse_args()

    asyncio.run(run_ingestion(
        limit=args.limit,
        delay_seconds=args.delay,
        exchange_filter=args.exchange
    ))
