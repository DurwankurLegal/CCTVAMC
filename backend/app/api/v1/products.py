from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.services import product as product_service

router = APIRouter()


@router.get("", response_model=List[ProductResponse])
async def list_products(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await product_service.list_products(db, current_user.tenant_id, offset, limit)


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    payload: ProductCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("products:write")),
):
    return await product_service.create_product(db, current_user.tenant_id, payload)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await product_service.get_product(db, current_user.tenant_id, product_id)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID, payload: ProductUpdate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("products:write")),
):
    return await product_service.update_product(db, current_user.tenant_id, product_id, payload)
