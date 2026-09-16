from fastapi import APIRouter
from core.database import check_db_connection
from core.redis_client import check_redis_connection

router = APIRouter(tags=["health"])

@router.get("/health/live")
async def liveness_check():
    """Liveness probe for orchestration: 'Is the API process running?'"""
    return {"status": "alive"}

@router.get("/health/ready")
async def readiness_check():
    """Readiness probe: 'Can this node serve traffic?'"""
    db_ok = await check_db_connection()
    redis_ok = await check_redis_connection()
    
    if db_ok and redis_ok:
        return {"status": "ready"}
    
    return {
        "status": "not_ready",
        "dependencies": {
            "database": "ok" if db_ok else "down",
            "redis": "ok" if redis_ok else "down"
        }
    }

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from core.database import get_db
from models.models import MarketCandle, Fundamental
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

def is_market_data_fresh(last_timestamp: datetime) -> str:
    """Session-aware market freshness."""
    if not last_timestamp:
        return "stale"
    
    now = datetime.now(timezone.utc)
    
    # Very basic session awareness for V1:
    # If today is weekend (Sat=5, Sun=6), Friday is acceptable.
    # Otherwise, it should be within 24 hours.
    # (A proper trading calendar is needed for holidays)
    elapsed = now - last_timestamp
    
    if now.weekday() in [5, 6]:
        if elapsed.total_seconds() < 72 * 3600:
            return "fresh"
    elif now.weekday() == 0 and now.hour < 4: # Monday before 9:30 AM IST (4:00 UTC)
        if elapsed.total_seconds() < 72 * 3600:
            return "fresh"
            
    if elapsed.total_seconds() < 24 * 3600:
        return "fresh"
        
    return "stale"

def is_fundamental_data_fresh(last_available: datetime) -> str:
    """Fundamentals can be up to 120 days old (quarterly reporting cycle + delays)."""
    if not last_available:
        return "stale"
    elapsed = datetime.now(timezone.utc) - last_available
    if elapsed.days < 120:
        return "fresh"
    return "stale"

@router.get("/health/data")
async def data_quality_check(db: AsyncSession = Depends(get_db)):
    """Check freshness of the data foundation."""
    # 1. Market Data
    candle_stmt = select(func.max(MarketCandle.timestamp))
    last_candle = (await db.execute(candle_stmt)).scalar()
    
    # 2. Fundamentals
    fund_stmt = select(func.max(Fundamental.as_of_date))  # fallback to as_of_date if available_at not populated yet
    last_fund = (await db.execute(fund_stmt)).scalar()
    
    market_status = is_market_data_fresh(last_candle) if last_candle else "stale"
    fund_status = is_fundamental_data_fresh(last_fund) if last_fund else "stale"
    
    return {
        "status": "healthy" if (market_status == "fresh" and fund_status == "fresh") else "degraded",
        "market_data": {
            "status": market_status,
            "last_timestamp": last_candle.isoformat() if last_candle else None
        },
        "fundamentals": {
            "status": fund_status,
            "last_available_at": last_fund.isoformat() if last_fund else None
        }
    }

@router.get("/health")
async def full_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed diagnostic endpoint."""
    db_ok = await check_db_connection()
    redis_ok = await check_redis_connection()
    
    return {
        "status": "healthy" if (db_ok and redis_ok) else "degraded",
        "services": {
            "api": "online",
            "database": "connected" if db_ok else "error",
            "redis": "connected" if redis_ok else "error"
        },
        "links": {
            "data_health": "/health/data"
        }
    }
