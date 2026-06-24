import pytest
from app.core.tenant_resolution import parse_tenant_slug_from_host

def test_parse_tenant_slug_from_host():
    base = "cctvamc.local"
    
    # Platform root matches should return None
    assert parse_tenant_slug_from_host("cctvamc.local", base) is None
    assert parse_tenant_slug_from_host("CctvAmc.Local", base) is None
    assert parse_tenant_slug_from_host("localhost", base) is None
    assert parse_tenant_slug_from_host("127.0.0.1", base) is None
    
    # Subdomain matches
    assert parse_tenant_slug_from_host("durwankur.cctvamc.local", base) == "durwankur"
    assert parse_tenant_slug_from_host("durwankur.cctvamc.local:8000", base) == "durwankur"
    assert parse_tenant_slug_from_host("DURWANKUR.cctvamc.local", base) == "durwankur"
    
    # Localhost subdomain matches
    assert parse_tenant_slug_from_host("durwankur.localhost", base) == "durwankur"
    assert parse_tenant_slug_from_host("durwankur.localhost:5173", base) == "durwankur"
    
    # Arbitrary domain or invalid checks
    assert parse_tenant_slug_from_host("greenvalley.in", base) is None
    assert parse_tenant_slug_from_host("", base) is None
    assert parse_tenant_slug_from_host(None, base) is None
