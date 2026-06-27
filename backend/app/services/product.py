from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import Product
from app.repositories.base import TenantRepository
from app.schemas.product import ProductCreate
from app.services.crud_base import make_crud


class ProductRepository(TenantRepository[Product]):
    model = Product


list_products, get_product_raw, create_product_raw, update_product = make_crud(ProductRepository, Product)


async def create_product(db: AsyncSession, tenant_id: UUID, payload: ProductCreate) -> Product:
    return await create_product_raw(db, tenant_id, payload)


async def get_product(db: AsyncSession, tenant_id: UUID, product_id: UUID) -> Product:
    return await get_product_raw(db, tenant_id, product_id)
