from typing import Generic, TypeVar, Optional, List, Type
from uuid import UUID
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base
from app.core.context import get_actor_id
from app.services import audit

ModelT = TypeVar("ModelT", bound=Base)


class TenantRepository(Generic[ModelT]):
    """Base repository that enforces tenant isolation and writes an audit log
    entry on every create/update/delete.

    ``_set_rls_context()`` sets the PostgreSQL session variable used by RLS
    policies. On PostgreSQL a failure to set it raises loudly (we must never
    silently run without RLS). On non-PostgreSQL backends (e.g. SQLite in
    tests) RLS does not exist and the statement is skipped — application-layer
    ``tenant_id`` filtering in every query still provides isolation.
    """

    model: Type[ModelT]

    def __init__(self, session: AsyncSession, tenant_id: UUID, actor_id: Optional[UUID] = None):
        self.session = session
        self.tenant_id = tenant_id
        # Fall back to the request-scoped actor when not explicitly provided.
        self.actor_id = actor_id if actor_id is not None else get_actor_id()

    async def _set_rls_context(self):
        conn = await self.session.connection()
        if conn.dialect.name == "postgresql":
            # Use set_config(..., is_local=true) — asyncpg does not accept bind
            # parameters in a plain ``SET`` statement. is_local=true scopes it to
            # the current transaction, equivalent to SET LOCAL.
            await self.session.execute(
                text("SELECT set_config('app.tenant_id', :tid, true)"),
                {"tid": str(self.tenant_id)},
            )

    @property
    def _entity_type(self) -> str:
        return self.model.__name__

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
        await audit.write_audit(
            self.session, self.tenant_id, self._entity_type, obj.id,
            "CREATE", None, audit.to_dict(obj), self.actor_id,
        )
        return obj

    async def save(self, obj: ModelT) -> ModelT:
        await self._set_rls_context()
        before, after = audit.diff(obj)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        if after:  # only log when something actually changed
            await audit.write_audit(
                self.session, self.tenant_id, self._entity_type, obj.id,
                "UPDATE", before, after, self.actor_id,
            )
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self._set_rls_context()
        snapshot = audit.to_dict(obj)
        entity_id = obj.id
        await self.session.delete(obj)
        await self.session.flush()
        await audit.write_audit(
            self.session, self.tenant_id, self._entity_type, entity_id,
            "DELETE", snapshot, None, self.actor_id,
        )
