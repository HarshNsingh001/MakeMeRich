"""
Alert Dispatcher — runs as part of the scheduler or can be called directly.

Checks all active user alerts against current market quotes and:
1. Triggers alerts that match their conditions
2. Creates Notification records in the DB
3. Publishes to Redis alert:{user_id} channel → picked up by WebSocket client in real-time

Alert conditions supported:
  PRICE_ABOVE   — ltp > threshold
  PRICE_BELOW   — ltp < threshold
  RSI_ABOVE     — rsi_14 > threshold
  RSI_BELOW     — rsi_14 < threshold
  OPPORTUNITY_HIGH     — a HIGH opportunity exists for the symbol
  OPPORTUNITY_MODERATE — a MODERATE or HIGH opportunity exists
"""
import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def dispatch_alerts():
    """
    Scan active alerts, check conditions against live data, notify matching users.
    Designed to run every 5-10 minutes during market hours.
    """
    from core.database import AsyncSessionLocal
    from core.redis_client import get_redis
    from models.models import Alert, AlertConditionEnum, Notification, MarketQuote, TechnicalIndicator, RecommendationSnapshot
    from sqlalchemy import select, desc, and_
    from services.market_stream import make_alert_channel

    logger.info("Alert dispatcher running...")
    triggered_count = 0

    async with AsyncSessionLocal() as db:
        # Fetch all active, un-triggered alerts
        stmt = select(Alert).where(Alert.is_active == True, Alert.triggered_at == None)
        alerts = (await db.execute(stmt)).scalars().all()

    for alert in alerts:
        try:
            triggered = False
            body = ""

            async with AsyncSessionLocal() as db:
                # Fetch latest quote
                quote_result = await db.execute(
                    select(MarketQuote).where(MarketQuote.symbol == alert.symbol)
                )
                quote = quote_result.scalar_one_or_none()
                ltp = float(quote.ltp) if quote and quote.ltp else None

                # Fetch latest technical indicator
                tech_result = await db.execute(
                    select(TechnicalIndicator).where(
                        TechnicalIndicator.symbol == alert.symbol
                    ).order_by(desc(TechnicalIndicator.timestamp)).limit(1)
                )
                tech = tech_result.scalar_one_or_none()
                rsi = float(tech.rsi_14) if tech and tech.rsi_14 else None

            threshold = float(alert.threshold_value) if alert.threshold_value else None
            condition = alert.condition

            # Evaluate condition
            if condition == AlertConditionEnum.PRICE_ABOVE and ltp and threshold:
                if ltp > threshold:
                    triggered = True
                    body = f"{alert.symbol} crossed above ₹{threshold:.2f} — now at ₹{ltp:.2f}"

            elif condition == AlertConditionEnum.PRICE_BELOW and ltp and threshold:
                if ltp < threshold:
                    triggered = True
                    body = f"{alert.symbol} dropped below ₹{threshold:.2f} — now at ₹{ltp:.2f}"

            elif condition == AlertConditionEnum.RSI_ABOVE and rsi and threshold:
                if rsi > threshold:
                    triggered = True
                    body = f"{alert.symbol} RSI is {rsi:.1f}, above your threshold of {threshold:.1f}"

            elif condition == AlertConditionEnum.RSI_BELOW and rsi and threshold:
                if rsi < threshold:
                    triggered = True
                    body = f"{alert.symbol} RSI is {rsi:.1f}, below your threshold of {threshold:.1f}"

            elif condition in (AlertConditionEnum.OPPORTUNITY_HIGH, AlertConditionEnum.OPPORTUNITY_MODERATE):
                # Check if there's a recent HIGH or MODERATE recommendation
                async with AsyncSessionLocal() as db:
                    opp_result = await db.execute(
                        select(RecommendationSnapshot).where(
                            RecommendationSnapshot.symbol == alert.symbol,
                            RecommendationSnapshot.is_active == True,
                        ).order_by(desc(RecommendationSnapshot.timestamp)).limit(1)
                    )
                    rec = opp_result.scalar_one_or_none()

                if rec:
                    level = rec.opportunity_level
                    if condition == AlertConditionEnum.OPPORTUNITY_HIGH and level == "HIGH":
                        triggered = True
                        body = f"{alert.symbol} — HIGH opportunity detected (confidence: {float(rec.confidence):.0%})"
                    elif condition == AlertConditionEnum.OPPORTUNITY_MODERATE and level in ("HIGH", "MODERATE"):
                        triggered = True
                        body = f"{alert.symbol} — {level} opportunity detected (confidence: {float(rec.confidence):.0%})"

            if not triggered:
                continue

            # Mark alert as triggered and create notification
            async with AsyncSessionLocal() as db:
                # Re-fetch to avoid session issues
                fresh_alert = (await db.execute(
                    select(Alert).where(Alert.id == alert.id)
                )).scalar_one_or_none()

                if not fresh_alert:
                    continue

                fresh_alert.triggered_at = datetime.utcnow()
                fresh_alert.is_active = False  # One-shot alert

                notification = Notification(
                    user_id=alert.user_id,
                    title=f"Alert: {alert.symbol}",
                    body=body,
                    related_symbol=alert.symbol,
                )
                db.add(notification)
                await db.commit()
                await db.refresh(notification)

            # Push real-time notification via Redis → WebSocket
            try:
                redis = await get_redis()
                payload = json.dumps({
                    "type": "alert",
                    "notification_id": notification.id,
                    "title": notification.title,
                    "body": notification.body,
                    "symbol": alert.symbol,
                    "ts": datetime.utcnow().isoformat(),
                })
                await redis.publish(make_alert_channel(alert.user_id), payload)
            except Exception as e:
                logger.warning(f"Failed to publish alert to Redis: {e}")

            triggered_count += 1
            logger.info(f"Alert triggered for user {alert.user_id}: {alert.symbol} — {condition.value}")

        except Exception as e:
            logger.error(f"Alert dispatch error for alert {alert.id}: {e}")

    logger.info(f"Alert dispatch complete. {triggered_count} alerts triggered.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(dispatch_alerts())
