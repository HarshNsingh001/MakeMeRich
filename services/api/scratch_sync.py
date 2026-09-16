import asyncio
from core.database import engine, Base
import models.models

async def init():
    async with engine.begin() as conn:
        from sqlalchemy import text
        try:
            await conn.execute(text("ALTER TABLE fundamentals ADD COLUMN published_at TIMESTAMP WITH TIME ZONE;"))
            await conn.execute(text("ALTER TABLE fundamentals ADD COLUMN available_at TIMESTAMP WITH TIME ZONE;"))
            await conn.execute(text("ALTER TABLE financial_periods ADD COLUMN published_at TIMESTAMP WITH TIME ZONE;"))
            await conn.execute(text("ALTER TABLE financial_periods ADD COLUMN available_at TIMESTAMP WITH TIME ZONE;"))
        except Exception as e:
            print("Error or already exists:", e)


asyncio.run(init())
