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

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 MakeMeRich API starting — env: %s", settings.app_env)
    yield
    logger.info("🛑 MakeMeRich API shutting down")
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
app.include_router(market_router)
app.include_router(stocks_router)
app.include_router(analysis_router)


@app.get("/", tags=["root"])
async def root():
    return {
        "name": "MakeMeRich API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
