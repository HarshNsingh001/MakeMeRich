"""
Sector Valuation Service — GAP-13

Computes sector-relative PE/PB/EV-EBITDA percentile ranks for any stock.

Why this matters (from the system design review):
  "A PE of 20x means nothing without context. Reliance at PE=20 is cheap
   vs its sector median of 27. HDFC Bank at PE=20 is expensive vs its
   sector median of 14. Absolute thresholds create alpha-destroying false signals."

Architecture:
  - Computes sector stats (median, mean, p25, p75) from the `fundamentals` table
  - Uses the `instruments` table for sector classification
  - PiT-safe: all queries filter by `fundamentals.as_of_date <= as_of`
  - Results are cached in Redis for 1 hour to avoid repeated aggregation queries
  - Cache key: `sector_valuation:{sector}:{date}`

Outputs:
  SectorValuationContext:
    pe_percentile:    0-100  (0 = cheapest in sector, 100 = most expensive)
    pb_percentile:    0-100
    sector_pe_median: float
    sector_pe_p25:    float   (bottom quartile cutoff — "cheap zone")
    sector_pe_p75:    float   (top quartile cutoff — "expensive zone")
    peer_count:       int     (number of sector peers with valid PE data)
    valuation_label:  "CHEAP" | "FAIR" | "EXPENSIVE"
"""
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func as sqlfunc

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 3600  # 1 hour
REDIS_KEY_PREFIX = "sector_valuation:"
MIN_PEERS_REQUIRED = 3  # Skip percentile if fewer than 3 peers with valid data


@dataclass
class SectorValuationContext:
    """Sector-relative valuation context for a single stock."""
    symbol: str
    sector: str

    # Stock's own values
    stock_pe: Optional[float]
    stock_pb: Optional[float]
    stock_ev_ebitda: Optional[float]

    # Sector PE stats
    pe_percentile: Optional[float]    # 0=cheapest, 100=most expensive in sector
    sector_pe_median: Optional[float]
    sector_pe_mean: Optional[float]
    sector_pe_p25: Optional[float]
    sector_pe_p75: Optional[float]
    sector_pe_min: Optional[float]
    sector_pe_max: Optional[float]

    # Sector PB stats
    pb_percentile: Optional[float]
    sector_pb_median: Optional[float]

    # Peer count
    peer_count: int

    # Derived label
    valuation_label: str     # "CHEAP" | "FAIR" | "EXPENSIVE" | "UNKNOWN"
    discount_to_median_pct: Optional[float]  # negative = cheaper than median

    # Metadata
    computed_at: str
    as_of_date: str


def _percentile_rank(value: float, sorted_values: List[float]) -> float:
    """
    Compute the percentile rank of `value` in `sorted_values`.
    Returns 0-100 where 100 = most expensive (highest value).
    """
    if not sorted_values:
        return 50.0
    n = len(sorted_values)
    # Count values strictly below
    below = sum(1 for v in sorted_values if v < value)
    # Count equal values
    equal = sum(1 for v in sorted_values if v == value)
    # Midpoint percentile (handles ties gracefully)
    return round((below + 0.5 * equal) / n * 100, 1)


def _compute_stats(values: List[float]) -> dict:
    """Compute descriptive stats from a list of floats."""
    if not values:
        return {"median": None, "mean": None, "p25": None, "p75": None, "min": None, "max": None}

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    def _quantile(q: float) -> float:
        """Linear interpolation quantile."""
        idx = (n - 1) * q
        lo, hi = int(idx), min(int(idx) + 1, n - 1)
        return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (idx - lo)

    return {
        "median": round(_quantile(0.5), 2),
        "mean": round(sum(sorted_vals) / n, 2),
        "p25": round(_quantile(0.25), 2),
        "p75": round(_quantile(0.75), 2),
        "min": round(sorted_vals[0], 2),
        "max": round(sorted_vals[-1], 2),
    }


async def _get_cached(redis_client, cache_key: str) -> Optional[dict]:
    try:
        raw = await redis_client.get(cache_key)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


async def _set_cached(redis_client, cache_key: str, data: dict):
    try:
        await redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(data))
    except Exception:
        pass


async def get_sector_pe_stats(
    db: AsyncSession,
    sector: str,
    as_of: datetime,
) -> dict:
    """
    Fetch PE and PB ratios for all active stocks in a sector and compute stats.
    Cached in Redis for 1 hour.

    Returns a dict of {symbol: pe, ...} and stats.
    """
    from core.redis_client import get_redis
    from models.models import Instrument, Fundamental

    cache_key = f"{REDIS_KEY_PREFIX}{sector}:{as_of.strftime('%Y-%m-%d')}"
    redis = await get_redis()

    # Try cache first
    cached = await _get_cached(redis, cache_key)
    if cached:
        return cached

    # Find all active symbols in this sector
    symbols_result = await db.execute(
        select(Instrument.symbol).where(
            and_(
                Instrument.sector == sector,
                Instrument.is_active == True,
            )
        )
    )
    sector_symbols = symbols_result.scalars().all()

    if not sector_symbols:
        return {"pe_values": {}, "pb_values": {}, "stats": {}, "peer_count": 0}

    # Fetch latest fundamentals for each symbol published before as_of
    # Use a subquery to get max as_of_date per symbol
    pe_data = {}
    pb_data = {}

    for symbol in sector_symbols:
        fund_result = await db.execute(
            select(Fundamental).where(
                and_(
                    Fundamental.symbol == symbol,
                    Fundamental.as_of_date <= as_of,
                )
            ).order_by(Fundamental.as_of_date.desc()).limit(1)
        )
        fund = fund_result.scalar_one_or_none()
        if not fund:
            continue

        # Only include positive PE (negative PE means company is loss-making — not comparable)
        if fund.pe_ratio and float(fund.pe_ratio) > 0:
            pe_data[symbol] = float(fund.pe_ratio)
        if fund.pb_ratio and float(fund.pb_ratio) > 0:
            pb_data[symbol] = float(fund.pb_ratio)

    pe_stats = _compute_stats(list(pe_data.values()))
    pb_stats = _compute_stats(list(pb_data.values()))

    result = {
        "sector": sector,
        "pe_values": pe_data,
        "pb_values": pb_data,
        "pe_stats": pe_stats,
        "pb_stats": pb_stats,
        "peer_count": len(pe_data),
        "computed_at": datetime.utcnow().isoformat(),
    }

    await _set_cached(redis, cache_key, result)
    return result


async def get_sector_valuation_context(
    db: AsyncSession,
    symbol: str,
    sector: str,
    stock_pe: Optional[float],
    stock_pb: Optional[float],
    stock_ev_ebitda: Optional[float],
    as_of: Optional[datetime] = None,
) -> SectorValuationContext:
    """
    Compute sector-relative valuation for a single stock.
    This is the main entry point for GAP-13.

    Args:
        db:              DB session
        symbol:          Stock symbol
        sector:          Stock's sector (from Instrument.sector)
        stock_pe:        Stock's current PE ratio
        stock_pb:        Stock's current PB ratio
        stock_ev_ebitda: Stock's current EV/EBITDA
        as_of:           Valuation date (PiT)
    """
    as_of = as_of or datetime.utcnow()

    if not sector:
        return SectorValuationContext(
            symbol=symbol, sector="Unknown",
            stock_pe=stock_pe, stock_pb=stock_pb, stock_ev_ebitda=stock_ev_ebitda,
            pe_percentile=None, sector_pe_median=None, sector_pe_mean=None,
            sector_pe_p25=None, sector_pe_p75=None, sector_pe_min=None, sector_pe_max=None,
            pb_percentile=None, sector_pb_median=None,
            peer_count=0, valuation_label="UNKNOWN",
            discount_to_median_pct=None,
            computed_at=datetime.utcnow().isoformat(),
            as_of_date=as_of.date().isoformat(),
        )

    # Get sector statistics
    sector_data = await get_sector_pe_stats(db, sector, as_of)
    pe_values = sector_data.get("pe_values", {})
    pb_values = sector_data.get("pb_values", {})
    pe_stats = sector_data.get("pe_stats", {})
    pb_stats = sector_data.get("pb_stats", {})
    peer_count = sector_data.get("peer_count", 0)

    # PE percentile
    pe_percentile = None
    discount_to_median_pct = None
    if stock_pe and stock_pe > 0 and peer_count >= MIN_PEERS_REQUIRED:
        all_pe_vals = list(pe_values.values())
        pe_percentile = _percentile_rank(stock_pe, all_pe_vals)

        median = pe_stats.get("median")
        if median and median > 0:
            discount_to_median_pct = round((stock_pe - median) / median * 100, 2)

    # PB percentile
    pb_percentile = None
    if stock_pb and stock_pb > 0 and len(pb_values) >= MIN_PEERS_REQUIRED:
        pb_percentile = _percentile_rank(stock_pb, list(pb_values.values()))

    # Derive valuation label from PE percentile
    valuation_label = "UNKNOWN"
    if pe_percentile is not None:
        if pe_percentile <= 33:
            valuation_label = "CHEAP"      # Bottom third of sector
        elif pe_percentile <= 66:
            valuation_label = "FAIR"       # Middle third
        else:
            valuation_label = "EXPENSIVE"  # Top third

    return SectorValuationContext(
        symbol=symbol,
        sector=sector,
        stock_pe=stock_pe,
        stock_pb=stock_pb,
        stock_ev_ebitda=stock_ev_ebitda,
        pe_percentile=pe_percentile,
        sector_pe_median=pe_stats.get("median"),
        sector_pe_mean=pe_stats.get("mean"),
        sector_pe_p25=pe_stats.get("p25"),
        sector_pe_p75=pe_stats.get("p75"),
        sector_pe_min=pe_stats.get("min"),
        sector_pe_max=pe_stats.get("max"),
        pb_percentile=pb_percentile,
        sector_pb_median=pb_stats.get("median"),
        peer_count=peer_count,
        valuation_label=valuation_label,
        discount_to_median_pct=discount_to_median_pct,
        computed_at=datetime.utcnow().isoformat(),
        as_of_date=as_of.date().isoformat(),
    )


async def get_all_sector_stats(db: AsyncSession, as_of: Optional[datetime] = None) -> List[dict]:
    """
    Compute valuation stats for every sector.
    Used by the market pulse dashboard to show sector rotation context.
    """
    from models.models import Instrument

    as_of = as_of or datetime.utcnow()

    # Get distinct sectors
    result = await db.execute(
        select(Instrument.sector).where(
            and_(Instrument.sector != None, Instrument.is_active == True)
        ).distinct()
    )
    sectors = [r for r in result.scalars().all() if r]

    all_stats = []
    for sector in sectors:
        try:
            data = await get_sector_pe_stats(db, sector, as_of)
            if data.get("peer_count", 0) < MIN_PEERS_REQUIRED:
                continue
            all_stats.append({
                "sector": sector,
                "peer_count": data["peer_count"],
                "pe_median": data["pe_stats"].get("median"),
                "pe_mean": data["pe_stats"].get("mean"),
                "pe_p25": data["pe_stats"].get("p25"),
                "pe_p75": data["pe_stats"].get("p75"),
                "pb_median": data["pb_stats"].get("median"),
            })
        except Exception as e:
            logger.warning(f"Sector stats failed for {sector}: {e}")

    # Sort by median PE ascending (cheapest sectors first)
    all_stats.sort(key=lambda x: x.get("pe_median") or 999)
    return all_stats
