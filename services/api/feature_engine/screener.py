"""
Quantitative Screener — V2

Implements the full PiT-native screening pipeline from the system design.

Architecture:
    Universe of instruments
          ↓
    Data Quality Gate (skip if score < 70)
          ↓
    Strategy Engine (GARP / Momentum / Value / Mean Reversion / Quality)
          ↓
    CAGR Enrichment (Revenue CAGR, EPS CAGR via HistoricalPeriods — GAP-12)
          ↓
    Ranked candidate list → LLM agents (next layer)

Key design constraints:
  - All data accessed via HistoricalSnapshot (Point-in-Time sealed)
  - Backtest mode: pass snapshot_override to use sealed historical data
  - Live mode: builds snapshots from latest DB rows (same PiT logic)
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.models import Instrument, TechnicalIndicator, Fundamental, FinancialPeriod
from feature_engine.strategy_engine import StrategyEngine, DEFAULT_STRATEGIES
from evaluation.backtester import HistoricalSnapshot, get_historical_snapshot
from services.sector_valuation import get_sector_valuation_context

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Data Quality Gate
# ─────────────────────────────────────────────

def compute_data_quality_score(snapshot: HistoricalSnapshot) -> tuple[int, list[str]]:
    """
    Score 0-100 for data completeness. Below 70 → skip AI analysis.
    Returns (score, list_of_issues).
    """
    score = 100
    issues = []

    fundamentals = snapshot.fundamentals
    technicals = snapshot.technicals

    # Fundamental checks
    if not fundamentals.get("pe_ratio"):
        score -= 25
        issues.append("Missing P/E ratio")
    if not fundamentals.get("roe"):
        score -= 20
        issues.append("Missing ROE")
    if not fundamentals.get("debt_to_equity") and fundamentals.get("debt_to_equity") != 0:
        score -= 10
        issues.append("Missing D/E ratio")

    # Technical checks
    if not technicals.get("rsi_14"):
        score -= 20
        issues.append("Missing RSI")
    if not technicals.get("volume_ratio"):
        score -= 10
        issues.append("Missing Volume Ratio")

    # Price check
    if not snapshot.price or snapshot.price <= 0:
        score -= 15
        issues.append("Missing or invalid price")

    return max(0, score), issues


# ─────────────────────────────────────────────
# CAGR Calculator (GAP-12)
# ─────────────────────────────────────────────

async def compute_cagr_metrics(db: AsyncSession, symbol: str, as_of: datetime) -> dict:
    """
    Compute Revenue CAGR and EPS CAGR from historical FinancialPeriod records.
    Only uses data published before `as_of` (PiT-safe).

    Returns:
        {
            "revenue_cagr_3y": float | None,
            "eps_cagr_3y": float | None,
            "revenue_cagr_5y": float | None,
            "eps_cagr_5y": float | None,
            "n_periods": int,
        }
    """
    result = await db.execute(
        select(FinancialPeriod)
        .where(
            and_(
                FinancialPeriod.symbol == symbol,
                FinancialPeriod.published_at <= as_of,  # PiT gate
            )
        )
        .order_by(FinancialPeriod.period_end.asc())
    )
    periods = result.scalars().all()

    if len(periods) < 2:
        return {"revenue_cagr_3y": None, "eps_cagr_3y": None,
                "revenue_cagr_5y": None, "eps_cagr_5y": None, "n_periods": len(periods)}

    def cagr(start_val, end_val, years: float) -> Optional[float]:
        if not start_val or not end_val or start_val <= 0 or years <= 0:
            return None
        try:
            return round(((end_val / start_val) ** (1 / years) - 1) * 100, 2)
        except Exception:
            return None

    latest = periods[-1]
    latest_year = latest.period_end.year if latest.period_end else None

    def find_period_n_years_ago(n: int):
        target_year = (latest_year or 2024) - n
        # Pick the closest period to target_year
        candidates = [p for p in periods if p.period_end and abs(p.period_end.year - target_year) <= 1]
        if not candidates:
            return None
        return min(candidates, key=lambda p: abs(p.period_end.year - target_year))

    period_3y = find_period_n_years_ago(3)
    period_5y = find_period_n_years_ago(5)

    return {
        "revenue_cagr_3y": cagr(
            float(period_3y.revenue) if period_3y and period_3y.revenue else None,
            float(latest.revenue) if latest.revenue else None,
            3.0,
        ) if period_3y else None,
        "eps_cagr_3y": cagr(
            float(period_3y.eps) if period_3y and period_3y.eps else None,
            float(latest.eps) if latest.eps else None,
            3.0,
        ) if period_3y else None,
        "revenue_cagr_5y": cagr(
            float(period_5y.revenue) if period_5y and period_5y.revenue else None,
            float(latest.revenue) if latest.revenue else None,
            5.0,
        ) if period_5y else None,
        "eps_cagr_5y": cagr(
            float(period_5y.eps) if period_5y and period_5y.eps else None,
            float(latest.eps) if latest.eps else None,
            5.0,
        ) if period_5y else None,
        "n_periods": len(periods),
    }


# ─────────────────────────────────────────────
# Main screener
# ─────────────────────────────────────────────

async def get_candidate_universe(
    db: AsyncSession,
    limit_per_strategy: int = 5,
    snapshot_override: Optional[Dict[str, HistoricalSnapshot]] = None,
    as_of: Optional[datetime] = None,
    max_symbols: int = 100,
) -> List[Dict[str, Any]]:
    """
    Run quantitative screens across the universe.

    If snapshot_override is provided (e.g. from the Backtester), it evaluates those
    snapshots strictly — PiT sealed, no live DB reads.
    Otherwise, fetches the latest state (live mode).

    Returns ranked list of candidates with strategy matches, DQ score, and CAGR metrics.
    """
    as_of = as_of or datetime.utcnow()
    logger.info(f"Running V3 Quantitative Screen | as_of={as_of.date()} | max_symbols={max_symbols}")

    engine = StrategyEngine(DEFAULT_STRATEGIES)
    candidates = {}  # symbol → result dict

    if snapshot_override:
        snapshots = list(snapshot_override.values())
    else:
        # Live mode — query active instruments and build PiT snapshots
        stmt = select(Instrument.symbol).where(Instrument.is_active == True).limit(max_symbols)
        symbols = (await db.execute(stmt)).scalars().all()

        snapshots = []
        for sym in symbols:
            snap = await get_historical_snapshot(db, sym, as_of)
            if snap:
                snapshots.append(snap)

    logger.info(f"Evaluating {len(snapshots)} snapshots...")

    for snap in snapshots:
        # 1. Data Quality Gate
        dq_score, dq_issues = compute_data_quality_score(snap)
        if dq_score < 70:
            logger.debug(f"[{snap.symbol}] Skipping — DQ score {dq_score}: {dq_issues}")
            continue

        # 2. Strategy Engine — evaluate all strategies
        matched = []
        strategy_details = {}
        total_score = 0.0

        for strategy_name in DEFAULT_STRATEGIES.keys():
            result = engine.evaluate(snap, strategy_name)
            strategy_details[strategy_name] = result
            if result["is_match"]:
                matched.append(strategy_name)
                total_score += result["score"]

        if not matched:
            continue

        # 3. CAGR Enrichment (GAP-12) — only for passed candidates to save DB queries
        cagr = await compute_cagr_metrics(db, snap.symbol, as_of)

        # 4. Sector Valuation Context (GAP-13)
        # Fetch sector for this symbol, then compute PE percentile within sector
        sector_ctx = None
        sector_bonus = 0.0
        try:
            # Get sector from Instrument table
            inst_result = await db.execute(
                select(Instrument.sector).where(Instrument.symbol == snap.symbol)
            )
            sector = inst_result.scalar_one_or_none()

            if sector:
                stock_pe = snap.fundamentals.get("pe_ratio")
                stock_pb = snap.fundamentals.get("pb_ratio")
                stock_ev_ebitda = snap.fundamentals.get("ev_ebitda")

                sector_ctx = await get_sector_valuation_context(
                    db=db,
                    symbol=snap.symbol,
                    sector=sector,
                    stock_pe=float(stock_pe) if stock_pe else None,
                    stock_pb=float(stock_pb) if stock_pb else None,
                    stock_ev_ebitda=float(stock_ev_ebitda) if stock_ev_ebitda else None,
                    as_of=as_of,
                )

                # Valuation bonus: reward stocks that are cheap vs their sector peers
                # CHEAP (pe_percentile <= 33) gets +15 pts — strong signal for Value/GARP
                if sector_ctx.valuation_label == "CHEAP":
                    sector_bonus = 15.0
                elif sector_ctx.valuation_label == "FAIR":
                    sector_bonus = 5.0
                # EXPENSIVE gets no bonus — already priced in

        except Exception as e:
            logger.debug(f"[{snap.symbol}] Sector valuation enrichment skipped: {e}")

        # 5. GARP bonus scoring: reward strong revenue growth
        garp_bonus = 0.0
        if "GARP" in matched:
            rev_cagr = cagr.get("revenue_cagr_3y")
            eps_cagr = cagr.get("eps_cagr_3y")
            if rev_cagr and rev_cagr >= 15:
                garp_bonus += 10  # +10 pts for revenue growing > 15% CAGR
            if eps_cagr and eps_cagr >= 15:
                garp_bonus += 10  # +10 pts for EPS growing > 15% CAGR

        total_bonus = garp_bonus + sector_bonus
        candidates[snap.symbol] = {
            "symbol": snap.symbol,
            "target_date": as_of.isoformat(),
            "matched_strategies": matched,
            "strategy_count": len(matched),
            "aggregate_score": round(total_score + total_bonus, 2),
            "garp_bonus": garp_bonus,
            "sector_bonus": sector_bonus,
            "data_quality_score": dq_score,
            "data_quality_issues": dq_issues,
            "cagr": cagr,
            "sector_valuation": (
                {
                    "sector": sector_ctx.sector,
                    "pe_percentile": sector_ctx.pe_percentile,
                    "valuation_label": sector_ctx.valuation_label,
                    "sector_pe_median": sector_ctx.sector_pe_median,
                    "discount_to_median_pct": sector_ctx.discount_to_median_pct,
                    "peer_count": sector_ctx.peer_count,
                }
                if sector_ctx else None
            ),
            "strategy_details": strategy_details,
            "snapshot_price": snap.price,
        }

    # Rank by: (1) number of matched strategies, (2) aggregate score
    sorted_cands = sorted(
        candidates.values(),
        key=lambda x: (x["strategy_count"], x["aggregate_score"]),
        reverse=True,
    )

    logger.info(f"Screening complete. {len(sorted_cands)} candidates passed all gates.")
    return sorted_cands
