"""
WebSocket stream router — WS /market/stream

Architecture (System Design Section 12):
    Redis Pub/Sub
         |
         v
    WebSocket Gateway (this module)
         |
         +----> Web / Android / iOS clients

Message Protocol (JSON over WebSocket):
    Client → Server:
        { "action": "subscribe",   "symbols": ["RELIANCE", "INFY"] }
        { "action": "unsubscribe", "symbols": ["RELIANCE"] }
        { "action": "ping" }

    Server → Client:
        { "type": "quote",   "symbol": "RELIANCE", "ltp": 2890.5, ... }
        { "type": "regime",  "regime": "BULL",  "confidence": 0.8, ... }
        { "type": "alert",   "title": "...", "body": "..." }
        { "type": "pong" }
        { "type": "error",   "detail": "..." }
        { "type": "subscribed",   "symbols": [...] }
        { "type": "unsubscribed", "symbols": [...] }

Security note:
    - Auth is optional via ?token= query param (JWT)
    - Unauthenticated clients get the market feed but not personal alerts
    - Authenticated clients additionally receive their alert notifications

Rate limits:
    - Max 10 symbols per client
    - Server heartbeat every 30 seconds to detect dead connections
"""
import asyncio
import json
import logging
from typing import Optional, Set, Dict
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.websockets import WebSocketState

from core.redis_client import get_redis
from services.market_stream import (
    market_stream_service,
    make_quote_channel,
    make_alert_channel,
    CHANNEL_ALL_QUOTES,
    CHANNEL_REGIME,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["stream"])

MAX_SYMBOLS_PER_CLIENT = 10
HEARTBEAT_INTERVAL = 30  # seconds


class WebSocketConnection:
    """Represents a single connected WebSocket client."""

    def __init__(self, websocket: WebSocket, user_id: Optional[int] = None):
        self.websocket = websocket
        self.user_id = user_id
        self.subscribed_symbols: Set[str] = set()
        self.connected_at = datetime.utcnow()
        self._listener_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def send(self, data: dict):
        """Send JSON message to client. Silently drop if connection closed."""
        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_json(data)
            except Exception:
                pass  # Connection closed mid-send

    async def send_error(self, detail: str):
        await self.send({"type": "error", "detail": detail})

    def _build_channel_list(self) -> list[str]:
        """Redis channels this client should subscribe to."""
        channels = [CHANNEL_REGIME]
        for symbol in self.subscribed_symbols:
            channels.append(make_quote_channel(symbol))
        if not self.subscribed_symbols:
            # No specific symbols → subscribe to the global market feed
            channels.append(CHANNEL_ALL_QUOTES)
        if self.user_id:
            channels.append(make_alert_channel(self.user_id))
        return channels

    async def listen_redis(self):
        """
        Subscribe to Redis pub/sub channels and forward messages to the WebSocket client.
        This runs in a dedicated background task per connection.
        """
        redis = await get_redis()
        # We need a separate Redis connection for pub/sub (cannot share with the pool)
        pubsub = redis.pubsub()

        try:
            while True:
                # (Re-)subscribe whenever symbol set changes
                channels = self._build_channel_list()
                await pubsub.subscribe(*channels)

                # Drain incoming messages
                async for raw_msg in pubsub.listen():
                    if raw_msg["type"] != "message":
                        continue
                    try:
                        data = json.loads(raw_msg["data"])
                        await self.send(data)
                    except Exception:
                        pass

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"Redis listener error: {e}")
        finally:
            try:
                await pubsub.unsubscribe()
                await pubsub.aclose()
            except Exception:
                pass

    async def send_heartbeat(self):
        """Periodic ping to detect dead connections."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await self.send({"type": "ping", "ts": datetime.utcnow().isoformat()})
        except asyncio.CancelledError:
            pass


class ConnectionManager:
    """Manages all active WebSocket connections."""

    def __init__(self):
        self._connections: Dict[str, WebSocketConnection] = {}

    def _conn_id(self, websocket: WebSocket) -> str:
        return str(id(websocket))

    def add(self, conn: WebSocketConnection):
        self._connections[self._conn_id(conn.websocket)] = conn
        # Tell the market stream service to track the symbols
        for sym in conn.subscribed_symbols:
            market_stream_service.add_symbol(sym)
        logger.info(f"WebSocket connected. Active connections: {len(self._connections)}")

    def remove(self, websocket: WebSocket):
        conn_id = self._conn_id(websocket)
        conn = self._connections.pop(conn_id, None)
        if conn:
            for sym in conn.subscribed_symbols:
                # Only remove from stream service if no other client is watching it
                still_needed = any(
                    sym in c.subscribed_symbols
                    for cid, c in self._connections.items()
                )
                if not still_needed:
                    market_stream_service.remove_symbol(sym)
        logger.info(f"WebSocket disconnected. Active connections: {len(self._connections)}")

    def get(self, websocket: WebSocket) -> Optional[WebSocketConnection]:
        return self._connections.get(self._conn_id(websocket))

    @property
    def count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


async def _authenticate(token: Optional[str]) -> Optional[int]:
    """Decode JWT token and return user_id, or None for unauthenticated."""
    if not token:
        return None
    try:
        from core.security import decode_access_token
        payload = decode_access_token(token)
        if payload:
            return int(payload.get("sub", 0)) or None
    except Exception:
        pass
    return None


@router.websocket("/market/stream")
async def market_stream(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None, description="JWT token for authenticated feed"),
    symbols: Optional[str] = Query(default=None, description="Comma-separated symbols to subscribe at connect"),
):
    """
    WebSocket endpoint for real-time market data streaming.

    Connect:
        ws://localhost:8000/market/stream
        ws://localhost:8000/market/stream?token=<jwt>&symbols=RELIANCE,INFY,TCS

    Messages (JSON):
        Subscribe:   {"action": "subscribe",   "symbols": ["RELIANCE"]}
        Unsubscribe: {"action": "unsubscribe", "symbols": ["RELIANCE"]}
        Ping:        {"action": "ping"}
    """
    await websocket.accept()

    # Auth (optional)
    user_id = await _authenticate(token)

    # Create connection object
    conn = WebSocketConnection(websocket=websocket, user_id=user_id)

    # Pre-subscribe to symbols from query param
    if symbols:
        initial_symbols = [s.strip().upper() for s in symbols.split(",") if s.strip()][:MAX_SYMBOLS_PER_CLIENT]
        for sym in initial_symbols:
            conn.subscribed_symbols.add(sym)
            market_stream_service.add_symbol(sym)

    manager.add(conn)

    # Send welcome message
    await conn.send({
        "type": "connected",
        "user_id": user_id,
        "subscribed_symbols": list(conn.subscribed_symbols),
        "message": "Connected to MakeMeRich market stream. Authenticated." if user_id else "Connected as guest.",
        "ts": datetime.utcnow().isoformat(),
    })

    # Start background listener task (Redis → WebSocket)
    conn._listener_task = asyncio.create_task(conn.listen_redis())
    conn._heartbeat_task = asyncio.create_task(conn.send_heartbeat())

    try:
        # Main loop — handle incoming client messages
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
            except asyncio.TimeoutError:
                # Client hasn't sent anything in 60s — check connection is alive
                if websocket.client_state != WebSocketState.CONNECTED:
                    break
                continue

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await conn.send_error("Invalid JSON")
                continue

            action = msg.get("action", "")

            if action == "ping":
                await conn.send({"type": "pong", "ts": datetime.utcnow().isoformat()})

            elif action == "subscribe":
                req_symbols = [s.strip().upper() for s in msg.get("symbols", [])]
                if len(conn.subscribed_symbols) + len(req_symbols) > MAX_SYMBOLS_PER_CLIENT:
                    await conn.send_error(f"Max {MAX_SYMBOLS_PER_CLIENT} symbols per connection")
                    continue
                for sym in req_symbols:
                    conn.subscribed_symbols.add(sym)
                    market_stream_service.add_symbol(sym)
                # Restart listener with new channels
                if conn._listener_task:
                    conn._listener_task.cancel()
                conn._listener_task = asyncio.create_task(conn.listen_redis())
                await conn.send({"type": "subscribed", "symbols": list(conn.subscribed_symbols)})

            elif action == "unsubscribe":
                req_symbols = [s.strip().upper() for s in msg.get("symbols", [])]
                for sym in req_symbols:
                    conn.subscribed_symbols.discard(sym)
                    # Only remove from stream service if no other clients care
                    if not any(sym in c.subscribed_symbols for c in manager._connections.values()):
                        market_stream_service.remove_symbol(sym)
                # Restart listener
                if conn._listener_task:
                    conn._listener_task.cancel()
                conn._listener_task = asyncio.create_task(conn.listen_redis())
                await conn.send({"type": "unsubscribed", "symbols": list(conn.subscribed_symbols)})

            else:
                await conn.send_error(f"Unknown action: {action}")

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected cleanly")
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
    finally:
        # Cleanup
        if conn._listener_task:
            conn._listener_task.cancel()
        if conn._heartbeat_task:
            conn._heartbeat_task.cancel()
        manager.remove(websocket)


@router.get("/market/stream/status")
async def stream_status():
    """Returns the number of active WebSocket connections and tracked symbols."""
    return {
        "active_connections": manager.count,
        "tracked_symbols": sorted(list(market_stream_service._subscribed_symbols)),
        "channels": {
            "regime": CHANNEL_REGIME,
            "global_quotes": CHANNEL_ALL_QUOTES,
            "per_symbol": f"quote:{{SYMBOL}}",
        }
    }
