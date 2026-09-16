from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from core.database import get_db
from models.models import TechnicalIndicator, MarketCandle, Fundamental, TimeframeEnum
from schemas.schemas import TechnicalOut, FundamentalsOut, ChartOut, CandleOut

router = APIRouter(prefix="/stocks", tags=["analysis"])


@router.get("/{symbol}/chart", response_model=ChartOut)
async def get_chart(
    symbol: str,
    exchange: str = Query(default="NSE"),
    timeframe: str = Query(default="1day", description="1min|5min|15min|30min|1hour|1day|1week"),
    limit: int = Query(default=200, ge=10, le=2000),
    db: AsyncSession = Depends(get_db),
):
    """Historical OHLCV candles for charting."""
    stmt = (
        select(MarketCandle)
        .where(
            MarketCandle.symbol == symbol.upper(),
            MarketCandle.exchange == exchange,
            MarketCandle.timeframe == timeframe,
        )
        .order_by(desc(MarketCandle.timestamp))
        .limit(limit)
    )
    result = await db.execute(stmt)
    candles = list(reversed(result.scalars().all()))

    return ChartOut(
        symbol=symbol.upper(),
        exchange=exchange,
        timeframe=timeframe,
        candles=[CandleOut.model_validate(c) for c in candles],
    )


@router.get("/{symbol}/technical", response_model=TechnicalOut)
async def get_technical(
    symbol: str,
    exchange: str = Query(default="NSE"),
    timeframe: str = Query(default="1day"),
    db: AsyncSession = Depends(get_db),
):
    """Latest technical indicators for a stock."""
    stmt = (
        select(TechnicalIndicator)
        .where(
            TechnicalIndicator.symbol == symbol.upper(),
            TechnicalIndicator.exchange == exchange,
            TechnicalIndicator.timeframe == timeframe,
        )
        .order_by(desc(TechnicalIndicator.timestamp))
        .limit(1)
    )
    result = await db.execute(stmt)
    ti = result.scalar_one_or_none()
    if not ti:
        raise HTTPException(
            status_code=404,
            detail=f"No technical indicators found for {symbol}. Run the feature engine first.",
        )
    return TechnicalOut.model_validate(ti)


@router.get("/{symbol}/fundamentals", response_model=FundamentalsOut)
async def get_fundamentals(
    symbol: str,
    exchange: str = Query(default="NSE"),
    db: AsyncSession = Depends(get_db),
):
    """Latest fundamental / valuation metrics for a stock."""
    stmt = (
        select(Fundamental)
        .where(
            Fundamental.symbol == symbol.upper(),
            Fundamental.exchange == exchange,
        )
        .order_by(desc(Fundamental.as_of_date))
        .limit(1)
    )
    result = await db.execute(stmt)
    fund = result.scalar_one_or_none()
    if not fund:
        raise HTTPException(
            status_code=404,
            detail=f"No fundamental data found for {symbol}. Ingest fundamentals first.",
        )
    return FundamentalsOut.model_validate(fund)
