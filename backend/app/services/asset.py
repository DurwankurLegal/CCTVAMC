from app.models.asset import CCTVAsset
from app.repositories.base import TenantRepository
from app.services.crud_base import make_crud


class AssetRepository(TenantRepository[CCTVAsset]):
    model = CCTVAsset


list_assets, get_asset, create_asset_raw, update_asset = make_crud(AssetRepository, CCTVAsset)


async def create_asset(db, tenant_id, payload):
    return await create_asset_raw(db, tenant_id, payload)
