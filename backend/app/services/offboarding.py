from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.tenant import Tenant
import importlib
import pkgutil
import app.models

async def export_tenant_data(db: AsyncSession, tenant_id: UUID) -> dict:
    """Gathers all records from tenant-scoped tables, serializes them to dictionaries,
    and returns a consolidated JSON-serializable structure (excluding passwords/keys)."""
    # Import all models to ensure metadata registration
    for module_info in pkgutil.iter_modules(app.models.__path__):
        importlib.import_module(f"app.models.{module_info.name}")
        
    from app.core.database import Base
    export_data = {}
    
    # Fetch tenant record
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return {}
        
    export_data["tenant"] = {
        "id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "plan": tenant.plan,
        "status": tenant.status,
        "branding": tenant.branding,
        "settings": tenant.settings,
        "gstin": tenant.gstin,
        "registered_address": tenant.registered_address,
        "invoice_prefix": tenant.invoice_prefix,
        "is_active": tenant.is_active,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
    }
    
    # Query all tables with a tenant_id column
    for table_name, table in Base.metadata.tables.items():
        if table_name == "tenants":
            continue
        if "tenant_id" in table.columns:
            stmt = select(table).where(table.c.tenant_id == tenant_id)
            res = await db.execute(stmt)
            rows = res.fetchall()
            
            table_rows = []
            for r in rows:
                row_dict = {}
                for col in table.columns:
                    val = getattr(r, col.name, None)
                    if val is None:
                        try:
                            val = r._mapping[col.name]
                        except Exception:
                            val = None
                            
                    # Omit credential/security tokens for security
                    if col.name in ("hashed_password", "handover_otp"):
                        continue
                        
                    if isinstance(val, UUID):
                        row_dict[col.name] = str(val)
                    elif hasattr(val, "isoformat"):
                        row_dict[col.name] = val.isoformat()
                    elif hasattr(val, "to_eng_string") or isinstance(val, float) or hasattr(val, "__float__"):
                        try:
                            row_dict[col.name] = float(val)
                        except Exception:
                            row_dict[col.name] = str(val)
                    else:
                        row_dict[col.name] = val
                table_rows.append(row_dict)
            export_data[table_name] = table_rows
            
    return export_data


async def hard_delete_tenant_data(db: AsyncSession, tenant_id: UUID) -> None:
    """Permanently delete all tables rows associated with this tenant,
    cleanup S3 uploaded media, and delete the tenant record itself."""
    for module_info in pkgutil.iter_modules(app.models.__path__):
        importlib.import_module(f"app.models.{module_info.name}")
        
    from app.core.database import Base
    from app.models.document import Document
    
    # Clean up files from S3/MinIO
    res = await db.execute(select(Document).where(Document.tenant_id == tenant_id))
    docs = res.scalars().all()
    if docs:
        from app.services.storage import delete_file
        for doc in docs:
            if doc.s3_key:
                delete_file(doc.s3_key)
                
    # Child-first deletion order to prevent FK violations
    ORDERED_DELETES = [
        "auth_sessions",
        "user_roles",
        "ticket_comments",
        "ticket_attachments",
        "pm_schedules",
        "installations",
        "payments",
        "invoices",
        "sales_orders",
        "quotations",
        "amc_assets",
        "amc_contracts",
        "cctv_assets",
        "customer_sites",
        "customer_contacts",
        "customer_portal_users",
        "customers",
        "leads",
        "vendors",
        "inventory_movements",
        "inventory_items",
        "notification_logs",
        "notification_templates",
        "audit_logs",
        "document_sequences",
        "documents",
        "dashboard_snapshots",
        "subscription_invoices",
        "users",
    ]
    
    for table_name in ORDERED_DELETES:
        if table_name in Base.metadata.tables:
            table = Base.metadata.tables[table_name]
            await db.execute(delete(table).where(table.c.tenant_id == tenant_id))
            
    # Finally remove the tenant itself
    await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
    await db.flush()
