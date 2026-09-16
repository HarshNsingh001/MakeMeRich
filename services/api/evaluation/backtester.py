import logging
import json
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from pydantic import BaseModel

from models.models import (
    Instrument, MarketCandle, TechnicalIndicator, Fundamental,
    BacktestExecution, BacktestCase, BacktestResult, ExchangeEnum,
    MarketRegimeFeature
)
from agents.graph import agent_pipeline

logger = logging.getLogger(__name__)

class HistoricalSnapshot(BaseModel):
    """Frozen point-in-time snapshot to prevent lookahead bias."""
    symbol: str
    target_date: datetime
    price: float
    technicals: Dict[str, float]
    fundamentals: Dict[str, float]
    market_regime: Dict[str, Any]

def hash_dict(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()

async def get_historical_snapshot(db: AsyncSession, symbol: str, target_date: datetime) -> Optional[HistoricalSnapshot]:
    """Builds a strict PiT snapshot of the market as it was known AT target_date."""
    
    # 1. Price & Technicals
    # Strictly where timestamp <= target_date
    candle_stmt = select(MarketCandle).where(
        and_(MarketCandle.symbol == symbol, MarketCandle.timestamp <= target_date)
    ).order_by(desc(MarketCandle.timestamp)).limit(1)
    
    candle = (await db.execute(candle_stmt)).scalar_one_or_none()
    if not candle:
        return None
        
    tech_stmt = select(TechnicalIndicator).where(
        and_(TechnicalIndicator.symbol == symbol, TechnicalIndicator.timestamp <= target_date)
    ).order_by(desc(TechnicalIndicator.timestamp)).limit(1)
    
    tech = (await db.execute(tech_stmt)).scalar_one_or_none()
    
    # 2. Fundamentals
    # Strictly where available_at <= target_date (or as_of_date if available_at not set for backward compat)
    fund_stmt = select(Fundamental).where(
        and_(
            Fundamental.symbol == symbol,
            Fundamental.as_of_date <= target_date
        )
    ).order_by(desc(Fundamental.as_of_date)).limit(1)
    
    fund = (await db.execute(fund_stmt)).scalar_one_or_none()
    
    # 3. Market Regime
    regime_stmt = select(MarketRegimeFeature).where(
        MarketRegimeFeature.date <= target_date
    ).order_by(desc(MarketRegimeFeature.date)).limit(1)
    
    regime = (await db.execute(regime_stmt)).scalar_one_or_none()
    
    snapshot = HistoricalSnapshot(
        symbol=symbol,
        target_date=target_date,
        price=float(candle.close),
        technicals={
            "RSI": float(tech.rsi_14) if tech and tech.rsi_14 else 50.0,
            "MACD": float(tech.macd) if tech and tech.macd else 0.0,
            "Volume_Ratio": float(tech.volume_ratio) if tech and tech.volume_ratio else 1.0,
        },
        fundamentals={
            "PE": float(fund.pe_ratio) if fund and fund.pe_ratio else 0.0,
            "ROE": float(fund.roe) if fund and fund.roe else 0.0,
            "Debt_to_Equity": float(fund.debt_to_equity) if fund and fund.debt_to_equity else 0.0,
        },
        market_regime={
            "regime": regime.regime.value if regime and regime.regime else "NEUTRAL",
            "vix": float(regime.india_vix) if regime and regime.india_vix else 15.0
        }
    )
    
    return snapshot

async def calculate_future_outcome(db: AsyncSession, symbol: str, target_date: datetime, t_days: int) -> dict:
    """Calculates entry, exit, and MAE/MFE for T+days horizon."""
    
    # Entry is the OPEN of the NEXT trading day
    entry_stmt = select(MarketCandle).where(
        and_(MarketCandle.symbol == symbol, MarketCandle.timestamp > target_date)
    ).order_by(MarketCandle.timestamp.asc()).limit(t_days)
    
    candles = (await db.execute(entry_stmt)).scalars().all()
    
    if not candles:
        return {"return": 0, "mae": 0, "mfe": 0}
        
    entry_price = float(candles[0].open)
    
    # If we don't have enough candles yet (e.g. recent dates), use the last available
    exit_candle = candles[-1]
    exit_price = float(exit_candle.close)
    
    # Calculate MAE (Max Adverse Excursion) and MFE (Max Favorable Excursion)
    min_low = min([float(c.low) for c in candles])
    max_high = max([float(c.high) for c in candles])
    
    mae = (min_low - entry_price) / entry_price
    mfe = (max_high - entry_price) / entry_price
    ret = (exit_price - entry_price) / entry_price
    
    return {
        "return": ret,
        "mae": mae,
        "mfe": mfe
    }

async def evaluate_case(db: AsyncSession, case: BacktestCase) -> bool:
    """
    Evaluates a single point-in-time case.
    Returns True if the pipeline produced a valid recommendation.
    """
    case.status = "RUNNING"
    await db.commit()
    
    try:
        # 1. Reconstruct exact PiT market state
        snapshot = await get_historical_snapshot(db, case.symbol, case.target_date)
        if not snapshot:
            raise ValueError(f"Could not reconstruct snapshot for {case.symbol} at {case.target_date}")
            
        case.input_snapshot_hash = hash_dict(snapshot.model_dump())
            
        # 2. Run Quantitative Screen on the PiT snapshot (V3 Architecture)
        from feature_engine.screener import get_candidate_universe
        candidates = await get_candidate_universe(db, limit_per_strategy=5, snapshot_override={case.symbol: snapshot})
        
        screener_context = None
        if candidates:
            # We are only evaluating this single symbol, so it should be the first one
            cand = candidates[0]
            screener_context = {
                "matched_strategies": cand["matched_strategies"],
                "score": cand["aggregate_score"]
            }
        else:
            logger.info(f"[{case.symbol}] Failed quantitative PiT screen. Still running AI for backtest completeness.")
            screener_context = {"matched_strategies": ["NONE_PASSED"], "score": 0}

        # 3. Construct GraphState
        initial_state = {
            "symbol": case.symbol,
            "market_data": {
                "ltp": float(snapshot.price),
                "technicals": snapshot.technicals,
                "fundamentals": snapshot.fundamentals,
                "regime": snapshot.market_regime
            },
            "screener_context": screener_context,
            "is_backtest": True,  # Critical flag to prevent agents from querying live DB
            "agent_status": "SUCCESS"
        }
        
        # 4. Execute AI Pipeline
        final_state = await agent_pipeline.ainvoke(initial_state)
        opportunity = final_state.get("opportunity_state")
        
        if not opportunity:
             raise ValueError("Agent pipeline failed to produce an opportunity state")
             
        # 4. Calculate Future Outcomes (T+5, T+10, T+20)
        out_t5 = await calculate_future_outcome(db, case.symbol, case.target_date, 5)
        out_t10 = await calculate_future_outcome(db, case.symbol, case.target_date, 10)
        out_t20 = await calculate_future_outcome(db, case.symbol, case.target_date, 20)
        
        # Calculate Nifty returns
        nifty_t5 = await calculate_future_outcome(db, "^NSEI", case.target_date, 5)
        
        # 5. Save Result
        result = BacktestResult(
            case_id=case.id,
            execution_id=case.execution_id,
            symbol=case.symbol,
            target_date=case.target_date,
            gross_return_t5=Decimal(str(out_t5["return"])),
            gross_return_t10=Decimal(str(out_t10["return"])),
            gross_return_t20=Decimal(str(out_t20["return"])),
            mae=Decimal(str(out_t20["mae"])),
            mfe=Decimal(str(out_t20["mfe"])),
            nifty_return_t5=Decimal(str(nifty_t5["return"])),
            opportunity_level=opportunity.opportunity_level,
            confidence=Decimal(str(opportunity.confidence)),
            risk_level=opportunity.risk_level,
            structured_evidence_json=final_state.get("technical_evidence", {}).model_dump() if final_state.get("technical_evidence") else {}
        )
        
        db.add(result)
        case.status = "COMPLETED"
        await db.commit()
        
    except Exception as e:
        logger.error(f"Case {case_id} failed: {e}")
        case.status = "FAILED"
        case.retries += 1
        await db.commit()
