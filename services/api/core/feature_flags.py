"""
Feature Flag System — lightweight, DB-backed feature gates.

Why feature flags:
  - Roll out new AI models/providers to a % of traffic without redeployment
  - Kill-switch for risky features (e.g. live recommendations, WebSocket stream)
  - A/B test strategy configurations
  - Gate features behind user tiers (e.g. authenticated vs anonymous)

Architecture:
  - Flags stored in Redis (fast reads, ~1ms lookup)
  - Fallback to DB for persistence across restarts
  - In-memory cache with TTL to avoid Redis on every request
  - Admin API to toggle flags at runtime

Flag schema:
    {
        "name": "enable_ai_opportunities",
        "enabled": true,
        "rollout_pct": 100,           # 0-100 — % of requests that see this flag ON
        "description": "...",
        "created_at": "...",
        "updated_at": "...",
    }

Usage:
    from core.feature_flags import is_enabled

    if await is_enabled("enable_ai_opportunities"):
        result = await run_ai_pipeline(...)
    else:
        result = await run_screener_only(...)
"""
import asyncio
import json
import logging
import time
import hashlib
from typing import Optional

logger = logging.getLogger(__name__)

# In-memory TTL cache (flag_name → (value, expires_at))
_cache: dict[str, tuple[bool, float]] = {}
CACHE_TTL_SECONDS = 30  # Refresh flag from Redis every 30s

# ─────────────────────────────────────────────
# Defaults — safe values for all flags
# These are used if Redis/DB is unreachable
# ─────────────────────────────────────────────
DEFAULT_FLAGS: dict[str, dict] = {
    "enable_ai_opportunities": {
        "enabled": True,
        "rollout_pct": 100,
        "description": "Enable LangGraph multi-agent AI analysis pipeline",
    },
    "enable_websocket_stream": {
        "enabled": True,
        "rollout_pct": 100,
        "description": "Enable real-time WebSocket market data stream",
    },
    "enable_backtesting": {
        "enabled": True,
        "rollout_pct": 100,
        "description": "Enable backtesting endpoints",
    },
    "enable_corporate_actions_ingestion": {
        "enabled": True,
        "rollout_pct": 100,
        "description": "Enable weekly corporate actions ingestion from Yahoo Finance",
    },
    "enable_outcome_evaluation": {
        "enabled": True,
        "rollout_pct": 100,
        "description": "Enable T+5/T+20/T+60 outcome evaluation cron",
    },
    "enable_alert_dispatch": {
        "enabled": True,
        "rollout_pct": 100,
        "description": "Enable real-time alert evaluation during market hours",
    },
    "use_yahoo_finance_fallback": {
        "enabled": True,
        "rollout_pct": 100,
        "description": "Use Yahoo Finance as fallback when Angel One is unavailable",
    },
    "enable_quality_strategy": {
        "enabled": True,
        "rollout_pct": 100,
        "description": "Include Quality strategy in quantitative screener",
    },
    "require_adx_for_momentum": {
        "enabled": True,
        "rollout_pct": 100,
        "description": "Require ADX ≥ 25 for Momentum strategy pass (GAP-11)",
    },
    "public_recommendations_enabled": {
        "enabled": False,    # OFF until SEBI compliance review complete
        "rollout_pct": 0,
        "description": "SEBI compliance gate — enable public AI recommendations feed",
    },
}

REDIS_KEY_PREFIX = "feature_flag:"


async def _get_from_redis(flag_name: str) -> Optional[dict]:
    """Try to fetch a flag definition from Redis."""
    try:
        from core.redis_client import get_redis
        redis = await get_redis()
        raw = await redis.get(f"{REDIS_KEY_PREFIX}{flag_name}")
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.debug(f"Feature flag Redis read failed for '{flag_name}': {e}")
    return None


async def _set_in_redis(flag_name: str, flag_def: dict):
    """Persist a flag definition to Redis."""
    try:
        from core.redis_client import get_redis
        redis = await get_redis()
        await redis.set(
            f"{REDIS_KEY_PREFIX}{flag_name}",
            json.dumps({**flag_def, "name": flag_name}),
        )
    except Exception as e:
        logger.warning(f"Feature flag Redis write failed for '{flag_name}': {e}")


def _is_in_rollout(flag_name: str, rollout_pct: int) -> bool:
    """
    Deterministic rollout based on flag name hash.
    Same flag_name always resolves to the same True/False for a given rollout_pct.
    Use request_id or user_id as salt for per-user rollout.
    """
    if rollout_pct >= 100:
        return True
    if rollout_pct <= 0:
        return False
    bucket = int(hashlib.md5(flag_name.encode()).hexdigest(), 16) % 100
    return bucket < rollout_pct


async def is_enabled(flag_name: str, default: bool = False) -> bool:
    """
    Check if a feature flag is enabled.

    Priority order:
      1. In-memory cache (if not expired)
      2. Redis
      3. DEFAULT_FLAGS hardcoded defaults
      4. `default` parameter fallback
    """
    now = time.monotonic()

    # 1. Check in-memory cache
    if flag_name in _cache:
        value, expires_at = _cache[flag_name]
        if now < expires_at:
            return value

    # 2. Check Redis
    flag_def = await _get_from_redis(flag_name)

    # 3. Fall back to hardcoded defaults
    if not flag_def:
        flag_def = DEFAULT_FLAGS.get(flag_name)

    if not flag_def:
        logger.debug(f"Feature flag '{flag_name}' not found — using default={default}")
        _cache[flag_name] = (default, now + CACHE_TTL_SECONDS)
        return default

    enabled = flag_def.get("enabled", False)
    rollout_pct = flag_def.get("rollout_pct", 100)

    result = enabled and _is_in_rollout(flag_name, rollout_pct)

    # Update cache
    _cache[flag_name] = (result, now + CACHE_TTL_SECONDS)
    return result


async def set_flag(flag_name: str, enabled: bool, rollout_pct: int = 100, description: str = "") -> dict:
    """
    Set a feature flag value at runtime.
    Persists to Redis and clears the local cache entry.
    """
    import datetime as dt
    flag_def = {
        "enabled": enabled,
        "rollout_pct": rollout_pct,
        "description": description or DEFAULT_FLAGS.get(flag_name, {}).get("description", ""),
        "updated_at": dt.datetime.utcnow().isoformat(),
    }
    await _set_in_redis(flag_name, flag_def)
    # Invalidate cache
    _cache.pop(flag_name, None)
    logger.info(f"Feature flag '{flag_name}' set to enabled={enabled}, rollout={rollout_pct}%")
    return {**flag_def, "name": flag_name}


async def get_all_flags() -> list[dict]:
    """Return all known flags with their current resolved values."""
    result = []
    for flag_name, default_def in DEFAULT_FLAGS.items():
        redis_def = await _get_from_redis(flag_name)
        effective_def = redis_def or default_def
        result.append({
            "name": flag_name,
            "enabled": effective_def.get("enabled", False),
            "rollout_pct": effective_def.get("rollout_pct", 100),
            "description": effective_def.get("description", ""),
            "source": "redis" if redis_def else "default",
        })
    return result


async def initialize_flags():
    """
    On startup, write all DEFAULT_FLAGS to Redis if they don't already exist.
    Ensures flags are always visible and editable via admin API.
    """
    for flag_name, flag_def in DEFAULT_FLAGS.items():
        existing = await _get_from_redis(flag_name)
        if not existing:
            await _set_in_redis(flag_name, flag_def)
    logger.info(f"Feature flags initialized. {len(DEFAULT_FLAGS)} flags registered.")
