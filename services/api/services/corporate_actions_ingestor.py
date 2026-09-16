"""
Corporate Actions ingestor — fetches splits, bonuses, dividends from Yahoo Finance
and persists them to the `corporate_actions` table.

Architectural note:
  - Angel One does not expose a corporate actions endpoint.
  - Yahoo Finance provides splits and dividends going back years.
  - These are tagged with data_source='yahoo_finance' so PiT backtests can
    verify the adjustment lineage.
  - Run this weekly (Sunday night) or on-demand.
"""
import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def ingest_corporate_actions_for_symbol(db: AsyncSession, symbol: str, exchange: str = "NSE") -> int:
    """Fetch and persist corporate actions for a single symbol. Returns count saved."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from providers.yahoo_finance import YahooFinanceProvider
    from models.models import CorporateAction, CorporateActionTypeEnum, ExchangeEnum

    provider = YahooFinanceProvider()
    try:
        actions = await provider.get_corporate_actions(symbol, exchange)
    except Exception as e:
        logger.warning(f"[{symbol}] Corporate action fetch failed: {e}")
        return 0

    saved = 0
    for action in actions:
        try:
            # Skip duplicates
            existing = await db.execute(
                select(CorporateAction).where(
                    CorporateAction.symbol == symbol,
                    CorporateAction.action_type == action.action_type,
                    CorporateAction.ex_date == action.ex_date,
                )
            )
            if existing.scalar_one_or_none():
                continue

            db.add(CorporateAction(
                symbol=symbol,
                exchange=ExchangeEnum(exchange),
                action_type=CorporateActionTypeEnum(action.action_type),
                ex_date=action.ex_date,
                record_date=action.record_date,
                ratio=action.ratio,
                amount=action.amount,
                remarks=action.remarks,
                data_source="yahoo_finance",
            ))
            saved += 1
        except Exception as e:
            logger.warning(f"[{symbol}] Failed to save action {action.action_type} on {action.ex_date}: {e}")

    await db.commit()
    return saved


async def run_corporate_actions_ingestion(batch_size: int = 50):
    """
    Iterate over all active instruments and ingest their corporate actions.
    Run weekly. Uses Yahoo Finance as the data source.
    """
    from core.database import AsyncSessionLocal
    from models.models import Instrument

    logger.info("Starting Corporate Actions ingestion job...")
    total_saved = 0

    async with AsyncSessionLocal() as db:
        stmt = select(Instrument.symbol).where(Instrument.is_active == True)
        symbols = (await db.execute(stmt)).scalars().all()

    for i, symbol in enumerate(symbols):
        async with AsyncSessionLocal() as db:
            n = await ingest_corporate_actions_for_symbol(db, symbol)
            total_saved += n
            if (i + 1) % 100 == 0:
                logger.info(f"Progress: {i + 1}/{len(symbols)} symbols | {total_saved} actions saved")

    logger.info(f"Corporate Actions ingestion complete. {total_saved} total actions saved for {len(symbols)} symbols.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_corporate_actions_ingestion())
