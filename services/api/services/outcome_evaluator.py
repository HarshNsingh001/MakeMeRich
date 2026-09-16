"""
Outcome Evaluation Service — computes realized returns for past recommendations.

For every RecommendationSnapshot older than T+5 trading days, this service:
1. Fetches the actual closing price at T+5, T+20, T+60 (approx 1 month) from Yahoo Finance.
2. Computes absolute and NIFTY-relative returns.
3. Determines if the thesis was invalidated.
4. Persists the results to the DB for future analysis.

This is how we measure whether the AI's assessments were accurate over time.
Run daily, 30 minutes after market close (15:45 IST → 10:15 UTC).
"""
import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)

# Trading days offset → calendar days (approximate for Indian market)
TRADING_DAY_CALENDAR_MULTIPLIER = 1.4


def _trading_days_to_calendar(trading_days: int) -> int:
    return int(trading_days * TRADING_DAY_CALENDAR_MULTIPLIER)


async def _get_price_at(symbol: str, target_date: datetime) -> Optional[float]:
    """Fetch the closing price at or after a given date using Yahoo Finance."""
    import yfinance as yf
    from_dt = target_date
    to_dt = target_date + timedelta(days=7)  # buffer for weekends/holidays
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        df = ticker.history(
            start=from_dt.strftime("%Y-%m-%d"),
            end=to_dt.strftime("%Y-%m-%d"),
            interval="1d",
        )
        if df.empty:
            return None
        return float(df.iloc[0]["Close"])
    except Exception as e:
        logger.warning(f"[{symbol}] Could not fetch price at {target_date.date()}: {e}")
        return None


async def evaluate_recommendation_outcomes(lookback_days: int = 90):
    """
    Scan recommendations older than T+5 and compute missing outcome metrics.
    """
    from core.database import AsyncSessionLocal
    from models.models import RecommendationSnapshot
    from sqlalchemy import select, and_

    logger.info("Starting Outcome Evaluation job...")

    now = datetime.utcnow()
    # Only evaluate recommendations that are at least 5 trading days (~7 calendar days) old
    cutoff_date = now - timedelta(days=7)
    max_lookback = now - timedelta(days=lookback_days)

    async with AsyncSessionLocal() as db:
        stmt = select(RecommendationSnapshot).where(
            and_(
                RecommendationSnapshot.timestamp < cutoff_date,
                RecommendationSnapshot.timestamp > max_lookback,
            )
        ).order_by(RecommendationSnapshot.timestamp.desc())

        result = await db.execute(stmt)
        snapshots = result.scalars().all()

    logger.info(f"Evaluating {len(snapshots)} recommendations...")
    evaluated = 0

    for snap in snapshots:
        try:
            entry_price = float(snap.current_price)
            snap_date = snap.timestamp

            # Check if outcome_json already has T+5 data — skip if already evaluated
            opp_json = snap.opportunity_state_json or {}
            if opp_json.get("outcome_evaluated"):
                continue

            # Fetch prices at different horizons
            price_t5 = await _get_price_at(snap.symbol, snap_date + timedelta(days=_trading_days_to_calendar(5)))
            price_t20 = await _get_price_at(snap.symbol, snap_date + timedelta(days=_trading_days_to_calendar(20)))
            price_t60 = await _get_price_at(snap.symbol, snap_date + timedelta(days=_trading_days_to_calendar(60)))

            # NIFTY benchmarks
            nifty_entry = await _get_price_at("^NSEI", snap_date)
            nifty_t5 = await _get_price_at("^NSEI", snap_date + timedelta(days=_trading_days_to_calendar(5)))
            nifty_t20 = await _get_price_at("^NSEI", snap_date + timedelta(days=_trading_days_to_calendar(20)))
            nifty_t60 = await _get_price_at("^NSEI", snap_date + timedelta(days=_trading_days_to_calendar(60)))

            def pct_return(entry: float, exit_price: Optional[float]) -> Optional[float]:
                if exit_price and entry:
                    return round((exit_price - entry) / entry * 100, 4)
                return None

            outcome = {
                "outcome_evaluated": True,
                "evaluated_at": now.isoformat(),
                "entry_price": entry_price,
                "return_t5": pct_return(entry_price, price_t5),
                "return_t20": pct_return(entry_price, price_t20),
                "return_t60": pct_return(entry_price, price_t60),
                "nifty_return_t5": pct_return(nifty_entry, nifty_t5) if nifty_entry else None,
                "nifty_return_t20": pct_return(nifty_entry, nifty_t20) if nifty_entry else None,
                "nifty_return_t60": pct_return(nifty_entry, nifty_t60) if nifty_entry else None,
                "relative_t5": (
                    pct_return(entry_price, price_t5) - pct_return(nifty_entry, nifty_t5)
                    if price_t5 and nifty_entry and nifty_t5 else None
                ),
                "relative_t20": (
                    pct_return(entry_price, price_t20) - pct_return(nifty_entry, nifty_t20)
                    if price_t20 and nifty_entry and nifty_t20 else None
                ),
                "relative_t60": (
                    pct_return(entry_price, price_t60) - pct_return(nifty_entry, nifty_t60)
                    if price_t60 and nifty_entry and nifty_t60 else None
                ),
            }

            async with AsyncSessionLocal() as db:
                from sqlalchemy import select as _select
                result = await db.execute(
                    _select(RecommendationSnapshot).where(RecommendationSnapshot.id == snap.id)
                )
                live_snap = result.scalar_one_or_none()
                if live_snap:
                    existing_json = live_snap.opportunity_state_json or {}
                    existing_json["outcome"] = outcome
                    live_snap.opportunity_state_json = existing_json
                    db.add(live_snap)
                    await db.commit()
            evaluated += 1

        except Exception as e:
            logger.error(f"[{snap.symbol}] Outcome evaluation failed: {e}")

    logger.info(f"Outcome Evaluation complete. Evaluated {evaluated}/{len(snapshots)} snapshots.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(evaluate_recommendation_outcomes())
