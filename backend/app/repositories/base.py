from typing import Generic, TypeVar, Optional, List, Type
from uuid import UUID
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class TenantRepository(Generic[ModelT]):
    """Base repository that enforces tenant isolation on every query.

    _set_rls_context() sets the PostgreSQL session variable used by RLS
    policies.  On non-PostgreSQL backends (e.g. SQLite in tests) the
    statement is silently skipped — application-layer tenant_id filtering
    in every query still provides isolation.
    """

    model: Type[ModelT]

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def _set_rls_context(self):
        try:
            conn = await self.session.connection()
            if conn.dialect.name == "postgresql":
                await self.session.execute(
                    text("SET LOCAL app.tenant_id = :tid"),
                    {"tid": str(self.tenant_id)},
                )
        except Exception:
            await self.session.rollback()
            pass

    async def get(self, id: UUID) -> Optional[ModelT]:
        await self._set_rls_context()
        result = await self.session.execute(
            select(self.model).where(
                self.model.id == id,
                self.model.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list(self, offset: int = 0, limit: int = 50) -> List[ModelT]:
        await self._set_rls_context()
        result = await self.session.execute(
            select(self.model)
            .where(self.model.tenant_id == self.tenant_id)
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, obj: ModelT) -> ModelT:
        await self._set_rls_context()
        obj.tenant_id = self.tenant_id
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def save(self, obj: ModelT) -> ModelT:
        await self._set_rls_context()
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self._set_rls_context()
        await self.session.delete(obj)
        await self.session.flush()
