from fastapi import APIRouter
from core.database import check_db_connection
from core.redis_client import check_redis_connection

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    db_ok = await check_db_connection()
    redis_ok = await check_redis_connection()
    all_ok = db_ok and redis_ok
    return {
        "status": "ok" if all_ok else "degraded",
        "db": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }
