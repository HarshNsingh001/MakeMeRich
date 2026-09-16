"""
MakeMeRich — Indian Equity Intelligence Platform
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.redis_client import close_redis
from routers.health import router as health_router
from routers.stocks import router as stocks_router
from routers.market import router as market_router
from routers.analysis import router as analysis_router
from routers.opportunities import router as opportunities_router
from routers.backtest import router as backtest_router
from routers.auth import router as auth_router
from routers.watchlists import router as watchlists_router
from routers.alerts import router as alerts_router
from routers.stream import router as stream_router
from routers.flags import router as flags_router
from services.market_stream import market_stream_service
from core.feature_flags import initialize_flags, is_enabled

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    import asyncio
    logger.info("🚀 MakeMeRich API starting — env: %s", settings.app_env)

    # Initialize feature flags (seed defaults to Redis)
    await initialize_flags()

    # Start the WebSocket market stream (gated by feature flag)
    _stream_task = None
    if await is_enabled("enable_websocket_stream"):
        _default_stream_symbols = [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
            "HINDUNILVR", "ITC", "SBIN", "BAJFINANCE", "KOTAKBANK",
        ]
        for sym in _default_stream_symbols:
            market_stream_service.add_symbol(sym)
        _stream_task = asyncio.create_task(market_stream_service.run())
        logger.info("WebSocket market stream started (%d default symbols)", len(_default_stream_symbols))
    else:
        logger.info("WebSocket stream disabled by feature flag")
    
    yield
    
    logger.info("🛑 MakeMeRich API shutting down")
    market_stream_service.stop()
    _stream_task.cancel()
    await close_redis()


app = FastAPI(
    title="MakeMeRich — Indian Equity Intelligence Platform",
    description=(
        "AI-assisted Indian equity research platform. "
        "Decision-support system — not a profit guarantee engine."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(market_router)
app.include_router(stocks_router)
app.include_router(analysis_router)
app.include_router(opportunities_router)
app.include_router(backtest_router)
app.include_router(watchlists_router)
app.include_router(alerts_router)
app.include_router(flags_router)      # Feature flags admin
app.include_router(stream_router)     # WebSocket stream


@app.get("/", tags=["root"])
async def root():
    return {
        "name": "MakeMeRich API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
