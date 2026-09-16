from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db
from models.models import Instrument, MarketQuote
from schemas.schemas import PaginatedStocksOut, InstrumentOut, StockDetailOut, QuoteOut

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("", response_model=PaginatedStocksOut)
async def list_stocks(
    search: str = Query(default="", description="Search by symbol or name"),
    sector: str = Query(default="", description="Filter by sector"),
    exchange: str = Query(default="NSE"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List and search the NSE equity universe."""
    stmt = select(Instrument).where(
        Instrument.is_active == True,
        Instrument.exchange == exchange,
    )
    if search:
        pattern = f"%{search.upper()}%"
        stmt = stmt.where(
            (Instrument.symbol.ilike(pattern)) | (Instrument.name.ilike(pattern))
        )
    if sector:
        stmt = stmt.where(Instrument.sector.ilike(f"%{sector}%"))

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Paginate
    stmt = stmt.offset((page - 1) * page_size).limit(page_size).order_by(Instrument.symbol)
    result = await db.execute(stmt)
    instruments = result.scalars().all()

    return PaginatedStocksOut(
        total=total,
        page=page,
        page_size=page_size,
        items=[InstrumentOut.model_validate(i) for i in instruments],
    )


@router.get("/{symbol}", response_model=StockDetailOut)
async def get_stock(
    symbol: str,
    exchange: str = Query(default="NSE"),
    db: AsyncSession = Depends(get_db),
):
    """Get stock profile and latest quote."""
    stmt = select(Instrument).where(
        Instrument.symbol == symbol.upper(),
        Instrument.exchange == exchange,
    )
    result = await db.execute(stmt)
    instrument = result.scalar_one_or_none()
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    quote_stmt = select(MarketQuote).where(
        MarketQuote.symbol == symbol.upper(),
        MarketQuote.exchange == exchange,
    )
    quote_result = await db.execute(quote_stmt)
    quote = quote_result.scalar_one_or_none()

    return StockDetailOut(
        instrument=InstrumentOut.model_validate(instrument),
        quote=QuoteOut.model_validate(quote) if quote else None,
    )
