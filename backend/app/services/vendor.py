from app.models.vendor import Vendor
from app.repositories.base import TenantRepository
from app.services.crud_base import make_crud


class VendorRepository(TenantRepository[Vendor]):
    model = Vendor


list_vendors, get_vendor, create_vendor_raw, update_vendor = make_crud(VendorRepository, Vendor)


async def create_vendor(db, tenant_id, payload):
    return await create_vendor_raw(db, tenant_id, payload)
