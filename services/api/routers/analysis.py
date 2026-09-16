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

@router.get("/{symbol}/analysis")
async def get_multi_agent_analysis(
    symbol: str,
    exchange: str = Query(default="NSE"),
    db: AsyncSession = Depends(get_db),
):
    """
    Run the LangGraph multi-agent pipeline to generate a decision synthesis.

    Injects real-time DB data (quote, technicals, fundamentals) and
    sector-relative valuation context (GAP-13) into the initial agent state.
    """
    from agents.graph import agent_pipeline
    from models.models import MarketQuote, Instrument, Fundamental
    from services.sector_valuation import get_sector_valuation_context
    from dataclasses import asdict

    sym = symbol.upper()

    # ── Fetch real data from DB ──────────────────────────────────────────────
    quote_result = await db.execute(
        select(MarketQuote).where(MarketQuote.symbol == sym, MarketQuote.exchange == exchange)
    )
    quote = quote_result.scalar_one_or_none()

    tech_result = await db.execute(
        select(TechnicalIndicator)
        .where(TechnicalIndicator.symbol == sym, TechnicalIndicator.exchange == exchange)
        .order_by(desc(TechnicalIndicator.timestamp)).limit(1)
    )
    tech = tech_result.scalar_one_or_none()

    fund_result = await db.execute(
        select(Fundamental)
        .where(Fundamental.symbol == sym, Fundamental.exchange == exchange)
        .order_by(desc(Fundamental.as_of_date)).limit(1)
    )
    fund = fund_result.scalar_one_or_none()

    inst_result = await db.execute(
        select(Instrument).where(Instrument.symbol == sym, Instrument.exchange == exchange)
    )
    instrument = inst_result.scalar_one_or_none()

    # ── Sector Valuation Context (GAP-13) ────────────────────────────────────
    sector_valuation_dict = None
    if instrument and instrument.sector:
        ctx = await get_sector_valuation_context(
            db=db,
            symbol=sym,
            sector=instrument.sector,
            stock_pe=float(fund.pe_ratio) if fund and fund.pe_ratio else None,
            stock_pb=float(fund.pb_ratio) if fund and fund.pb_ratio else None,
            stock_ev_ebitda=float(fund.ev_ebitda) if fund and fund.ev_ebitda else None,
        )
        sector_valuation_dict = asdict(ctx)

    # ── Build initial graph state ─────────────────────────────────────────────
    initial_state = {
        "symbol": sym,
        "market_data": {
            "ltp": float(quote.ltp) if quote else None,
            "change_pct": float(quote.change_pct) if quote and quote.change_pct else None,
            "technicals": {
                "rsi_14": float(tech.rsi_14) if tech and tech.rsi_14 else None,
                "adx_14": float(tech.adx_14) if tech and tech.adx_14 else None,
                "volume_ratio": float(tech.volume_ratio) if tech and tech.volume_ratio else None,
                "ema_50": float(tech.ema_50) if tech and tech.ema_50 else None,
                "ema_200": float(tech.ema_200) if tech and tech.ema_200 else None,
                "macd": float(tech.macd) if tech and tech.macd else None,
                "bb_upper": float(tech.bb_upper) if tech and tech.bb_upper else None,
                "bb_lower": float(tech.bb_lower) if tech and tech.bb_lower else None,
            } if tech else {},
            "fundamentals": {
                "pe_ratio": float(fund.pe_ratio) if fund and fund.pe_ratio else None,
                "pb_ratio": float(fund.pb_ratio) if fund and fund.pb_ratio else None,
                "ev_ebitda": float(fund.ev_ebitda) if fund and fund.ev_ebitda else None,
                "promoter_holding_pct": float(fund.promoter_holding_pct) if fund and fund.promoter_holding_pct else None,
                "fii_holding_pct": float(fund.fii_holding_pct) if fund and fund.fii_holding_pct else None,
            } if fund else {},
        },
        "sector_valuation": sector_valuation_dict,  # GAP-13
    }

    final_state = await agent_pipeline.ainvoke(initial_state)

    return {
        "symbol": sym,
        "sector": instrument.sector if instrument else None,
        "sector_valuation": sector_valuation_dict,
        "opportunity_state": final_state.get("opportunity_state"),
        "evidence": {
            "market_regime": final_state.get("market_regime_evidence"),
            "historical": final_state.get("historical_evidence"),
            "technical": final_state.get("technical_evidence"),
            "fundamental": final_state.get("fundamental_evidence"),
            "entry": final_state.get("entry_evidence"),
            "risk": final_state.get("risk_evidence"),
        },
        "critic_feedback": final_state.get("critic_feedback"),
        "is_valid": final_state.get("is_valid"),
    }
