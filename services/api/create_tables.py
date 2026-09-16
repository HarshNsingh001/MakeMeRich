"""
Creates all new tables defined in models.py that don't yet exist in the DB.
Uses create_all with checkfirst=True — safe to run multiple times.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import get_settings
from core.database import Base

# Import ALL models so SQLAlchemy knows about them
import models.models  # noqa: F401

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    await engine.dispose()
    print("✅ All tables created/verified.")

if __name__ == "__main__":
    asyncio.run(main())
