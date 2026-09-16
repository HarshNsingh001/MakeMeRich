from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from core.database import get_db
from models.models import MarketRegimeFeature
from schemas.schemas import MarketOverviewOut

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/overview", response_model=MarketOverviewOut)
async def get_market_overview(
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the latest market regime snapshot:
    NIFTY close, EMA 50/200, India VIX, advance/decline ratio, regime label.
    """
    stmt = (
        select(MarketRegimeFeature)
        .order_by(desc(MarketRegimeFeature.date))
        .limit(1)
    )
    result = await db.execute(stmt)
    regime = result.scalar_one_or_none()

    if not regime:
        from datetime import datetime
        return MarketOverviewOut(
            date=datetime.utcnow(),
            regime="NEUTRAL",
            regime_confidence=None,
            nifty_close=None,
            nifty_change_pct=None,
            nifty_ema_50=None,
            nifty_ema_200=None,
            india_vix=None,
            advance_decline_ratio=None,
            advances=None,
            declines=None,
        )

    return MarketOverviewOut(
        date=regime.date,
        regime=regime.regime.value if regime.regime else "NEUTRAL",
        regime_confidence=regime.regime_confidence,
        nifty_close=regime.nifty_close,
        nifty_change_pct=regime.nifty_change_pct,
        nifty_ema_50=regime.nifty_ema_50,
        nifty_ema_200=regime.nifty_ema_200,
        india_vix=regime.india_vix,
        advance_decline_ratio=regime.advance_decline_ratio,
        advances=regime.advances,
        declines=regime.declines,
    )
