from __future__ import annotations

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# ── Lazy engine initialisation ─────────────────────────────────────────────
# We deliberately do NOT call get_settings() at module-import time so that
# importing `Base` (e.g. in Alembic env.py) never requires env vars to be set.
_engine = None
_AsyncSessionLocal = None


def _init_engine():
    global _engine, _AsyncSessionLocal
    if _engine is not None:
        return
    from app.core.config import get_settings
    settings = get_settings()
    _engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=10,
        max_overflow=20,
    )
    _AsyncSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)


def get_engine():
    _init_engine()
    return _engine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    _init_engine()
    async with _AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
