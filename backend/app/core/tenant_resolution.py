from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.tenant import Tenant

def parse_tenant_slug_from_host(host: str, base_domain: str) -> Optional[str]:
    """Parse the subdomain (tenant slug) from the host header.
    
    If the host matches base_domain or localhost/127.0.0.1, it's considered the platform root.
    Otherwise, if it ends with base_domain (or .localhost), the subdomain is extracted.
    Returns None if no subdomain can be extracted or if it's the root domain.
    """
    if not host:
        return None
    # Strip port if present
    clean_host = host.split(":")[0].lower().strip()
    
    # Platform root checks
    if clean_host in (base_domain.lower(), "localhost", "127.0.0.1"):
        return None
        
    # Check if ends with .base_domain
    if clean_host.endswith(f".{base_domain.lower()}"):
        slug = clean_host[:-len(base_domain) - 1]
        return slug if slug else None
        
    # Local development helper: e.g. company.localhost
    if clean_host.endswith(".localhost"):
        slug = clean_host[:-10]
        return slug if slug else None
        
    return None

async def resolve_tenant_from_host(db: AsyncSession, host: str, base_domain: str) -> Optional[Tenant]:
    """Resolve the tenant object from the Host header.
    
    First tries to parse the host as a subdomain to find a matching tenant slug.
    If no subdomain matches, checks if the host is configured as a custom domain
    for any tenant.
    """
    if not host:
        return None
    clean_host = host.split(":")[0].lower().strip()
    
    # Try parsing as subdomain/slug first
    slug = parse_tenant_slug_from_host(clean_host, base_domain)
    if slug:
        result = await db.execute(select(Tenant).where(Tenant.slug == slug, Tenant.is_active == True))
        tenant = result.scalar_one_or_none()
        if tenant:
            return tenant
            
    # Try matching custom domain
    result = await db.execute(select(Tenant).where(Tenant.custom_domain == clean_host, Tenant.is_active == True))
    tenant = result.scalar_one_or_none()
    return tenant
