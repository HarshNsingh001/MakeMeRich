"""
Market Stream Service — the "Market Data Collector" layer from the system design.

Architecture (Section 12):
    Broker / market WebSocket
         |
         v
    MarketStreamService (this module)
         |
         +----> validation / normalization
         |
         v
    Redis Pub/Sub channels
         |
         +----> "quote:RELIANCE"   — per-symbol quote channel
         +----> "quote:__all__"    — global market feed
         +----> "market:regime"    — regime updates
         |
         v
    FastAPI WebSocket Gateway (routers/stream.py)
         |
         +----> Web / Android / iOS clients

Why Redis Pub/Sub:
  - Multiple clients subscribe independently
  - No direct broker connection per client (rate limiting, auth, normalization handled once)
  - Works with existing redis.asyncio dependency
  - Decoupled: swap broker adapter without touching WebSocket layer

Channel naming convention:
  quote:{SYMBOL}   — e.g. "quote:RELIANCE", "quote:INFY"
  quote:__all__    — all symbols broadcast (market feed)
  market:regime    — current regime classification update
  alert:{USER_ID}  — triggered alert notifications for a user
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Set

logger = logging.getLogger(__name__)

# How often we push quote updates (seconds)
# During market hours this could be ~5s; off-hours ~60s
QUOTE_POLL_INTERVAL_SECONDS = 10
REGIME_REFRESH_INTERVAL_SECONDS = 300  # 5 minutes

# Channel names
CHANNEL_ALL_QUOTES = "quote:__all__"
CHANNEL_REGIME = "market:regime"


def make_quote_channel(symbol: str) -> str:
    return f"quote:{symbol.upper()}"


def make_alert_channel(user_id: int) -> str:
    return f"alert:{user_id}"


class MarketStreamService:
    """
    Polls market data and publishes normalized updates to Redis channels.
    One instance runs per application — clients subscribe via WebSocket.
    """

    def __init__(self):
        self._running = False
        self._subscribed_symbols: Set[str] = set()

    def add_symbol(self, symbol: str):
        self._subscribed_symbols.add(symbol.upper())

    def remove_symbol(self, symbol: str):
        self._subscribed_symbols.discard(symbol.upper())

    async def _publish_quote(self, redis_client, symbol: str):
        """Fetch latest quote for a symbol and publish to Redis."""
        from core.database import AsyncSessionLocal
        from models.models import MarketQuote
        from sqlalchemy import select

        try:
            async with AsyncSessionLocal() as db:
                stmt = select(MarketQuote).where(MarketQuote.symbol == symbol)
                result = await db.execute(stmt)
                quote = result.scalar_one_or_none()

            if not quote:
                return

            payload = {
                "type": "quote",
                "symbol": symbol,
                "ltp": float(quote.ltp) if quote.ltp else None,
                "open": float(quote.open) if quote.open else None,
                "high": float(quote.high) if quote.high else None,
                "low": float(quote.low) if quote.low else None,
                "close": float(quote.close) if quote.close else None,
                "volume": int(quote.volume) if quote.volume else None,
                "change": float(quote.change) if quote.change else None,
                "change_pct": float(quote.change_pct) if quote.change_pct else None,
                "timestamp": quote.quote_timestamp.isoformat() if quote.quote_timestamp else None,
                "published_at": datetime.utcnow().isoformat(),
            }

            msg = json.dumps(payload)
            # Publish to per-symbol channel and the global feed
            await redis_client.publish(make_quote_channel(symbol), msg)
            await redis_client.publish(CHANNEL_ALL_QUOTES, msg)

        except Exception as e:
            logger.warning(f"[{symbol}] Quote publish failed: {e}")

    async def _publish_regime(self, redis_client):
        """Fetch latest market regime and publish to Redis."""
        from core.database import AsyncSessionLocal
        from models.models import MarketRegimeFeature
        from sqlalchemy import select, desc

        try:
            async with AsyncSessionLocal() as db:
                stmt = select(MarketRegimeFeature).order_by(desc(MarketRegimeFeature.date)).limit(1)
                result = await db.execute(stmt)
                regime = result.scalar_one_or_none()

            if not regime:
                return

            payload = {
                "type": "regime",
                "regime": regime.regime.value if regime.regime else "NEUTRAL",
                "confidence": float(regime.regime_confidence) if regime.regime_confidence else None,
                "nifty_close": float(regime.nifty_close) if regime.nifty_close else None,
                "nifty_change_pct": float(regime.nifty_change_pct) if regime.nifty_change_pct else None,
                "india_vix": float(regime.india_vix) if regime.india_vix else None,
                "advance_decline_ratio": float(regime.advance_decline_ratio) if regime.advance_decline_ratio else None,
                "date": regime.date.isoformat() if regime.date else None,
                "published_at": datetime.utcnow().isoformat(),
            }
            await redis_client.publish(CHANNEL_REGIME, json.dumps(payload))

        except Exception as e:
            logger.warning(f"Regime publish failed: {e}")

    async def run(self):
        """
        Main loop — polls at QUOTE_POLL_INTERVAL_SECONDS and pushes to Redis.
        Run this as a background asyncio task in the FastAPI lifespan.
        """
        from core.redis_client import get_redis

        self._running = True
        logger.info("MarketStreamService started")
        regime_tick = 0

        while self._running:
            try:
                redis_client = await get_redis()

                # Publish all subscribed symbol quotes
                symbols = list(self._subscribed_symbols)
                for symbol in symbols:
                    await self._publish_quote(redis_client, symbol)

                # Publish regime update every N ticks
                regime_tick += 1
                if regime_tick * QUOTE_POLL_INTERVAL_SECONDS >= REGIME_REFRESH_INTERVAL_SECONDS:
                    await self._publish_regime(redis_client)
                    regime_tick = 0

            except Exception as e:
                logger.error(f"MarketStreamService loop error: {e}")

            await asyncio.sleep(QUOTE_POLL_INTERVAL_SECONDS)

    def stop(self):
        self._running = False


# Singleton — shared across the whole application lifecycle
market_stream_service = MarketStreamService()
