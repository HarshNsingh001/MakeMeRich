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


@router.get("/{symbol}/sector-valuation")
async def get_sector_valuation(
    symbol: str,
    exchange: str = Query(default="NSE"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get sector-relative valuation for a stock (GAP-13).

    Returns PE percentile rank vs sector peers, sector median PE,
    discount/premium to sector median, and a CHEAP/FAIR/EXPENSIVE label.

    Example response:
        {
          "symbol": "HDFCBANK",
          "sector": "Financial Services",
          "pe_percentile": 28.5,       # cheaper than 71% of banking peers
          "valuation_label": "CHEAP",
          "sector_pe_median": 18.4,
          "discount_to_median_pct": -15.2,  # 15% cheaper than sector median
          "peer_count": 42
        }
    """
    from services.sector_valuation import get_sector_valuation_context
    from models.models import Fundamental

    inst_result = await db.execute(
        select(Instrument).where(
            Instrument.symbol == symbol.upper(),
            Instrument.exchange == exchange,
        )
    )
    instrument = inst_result.scalar_one_or_none()
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    # Get latest fundamentals
    fund_result = await db.execute(
        select(Fundamental).where(
            Fundamental.symbol == symbol.upper(),
            Fundamental.exchange == exchange,
        ).order_by(Fundamental.as_of_date.desc()).limit(1)
    )
    fund = fund_result.scalar_one_or_none()

    from datetime import datetime
    ctx = await get_sector_valuation_context(
        db=db,
        symbol=symbol.upper(),
        sector=instrument.sector,
        stock_pe=float(fund.pe_ratio) if fund and fund.pe_ratio else None,
        stock_pb=float(fund.pb_ratio) if fund and fund.pb_ratio else None,
        stock_ev_ebitda=float(fund.ev_ebitda) if fund and fund.ev_ebitda else None,
        as_of=datetime.utcnow(),
    )
    from dataclasses import asdict
    return asdict(ctx)


@router.get("/sectors/summary")
async def get_sectors_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Sector rotation dashboard — median PE/PB for all sectors.
    Sorted from cheapest to most expensive.
    Cached in Redis for 1 hour.
    """
    from services.sector_valuation import get_all_sector_stats
    return await get_all_sector_stats(db)
