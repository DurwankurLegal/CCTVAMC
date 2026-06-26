"""
Generic CRUD factory — produces list/get/create/update functions for any
TenantRepository so simple modules don't need to repeat boilerplate.
"""
from typing import Type, TypeVar
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.repositories.base import TenantRepository
from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


def make_crud(repo_cls: Type[TenantRepository], model_cls: Type[ModelT]):
    async def _list(db: AsyncSession, tenant_id: UUID, offset: int = 0, limit: int = 50):
        return await repo_cls(db, tenant_id).list(offset=offset, limit=limit)

    async def _get(db: AsyncSession, tenant_id: UUID, obj_id: UUID) -> ModelT:
        obj = await repo_cls(db, tenant_id).get(obj_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"{model_cls.__name__} not found")
        return obj

    async def _create(db: AsyncSession, tenant_id: UUID, payload, extra: dict = None) -> ModelT:
        data = payload.model_dump(exclude_none=False)
        if extra:
            data.update(extra)
        if hasattr(model_cls, "company_id") and not data.get("company_id"):
            from app.services.company import resolve_company_id
            data["company_id"] = await resolve_company_id(db, tenant_id, None)
        obj = model_cls(**data)
        return await repo_cls(db, tenant_id).create(obj)

    async def _update(db: AsyncSession, tenant_id: UUID, obj_id: UUID, payload) -> ModelT:
        repo = repo_cls(db, tenant_id)
        obj = await repo.get(obj_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"{model_cls.__name__} not found")
        for k, v in payload.model_dump(exclude_none=True).items():
            setattr(obj, k, v)
        return await repo.save(obj)

    return _list, _get, _create, _update
