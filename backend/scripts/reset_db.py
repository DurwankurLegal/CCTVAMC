import asyncio
from sqlalchemy import text
from app.core.database import get_engine

async def reset_db() -> None:
    engine = get_engine()
    print("🧹 Cleaning database...")
    async with engine.begin() as conn:
        # Drop the public schema and recreate it
        await conn.execute(text("DROP SCHEMA public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA public;"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
    print("✔ Database reset successfully.")

if __name__ == "__main__":
    asyncio.run(reset_db())
