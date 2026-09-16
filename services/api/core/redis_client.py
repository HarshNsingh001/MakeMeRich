import redis.asyncio as aioredis
from core.config import get_settings

settings = get_settings()

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency — returns a shared async Redis client."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


async def check_redis_connection() -> bool:
    """Health check — returns True if Redis is reachable."""
    try:
        client = await get_redis()
        return await client.ping()
    except Exception:
        return False


async def close_redis():
    """Close Redis connection pool on shutdown."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
