import pytest
import uuid
from datetime import datetime, timezone
from app.models.user import User, TenantRole
from app.models.tenant import Tenant
from app.core.security import hash_password

async def _seed_tenant_admin_and_tech(db, slug):
    # Seed tenant
    t = Tenant(id=uuid.uuid4(), name=f"Company {slug}", slug=slug, plan="growth", status="active", is_active=True)
    db.add(t)
    await db.flush()
    
    # Seed admin
    admin = User(
        id=uuid.uuid4(), tenant_id=t.id, email=f"admin@{slug}.com",
        full_name="Admin User", hashed_password=hash_password("Pass@1234"),
        role=TenantRole.ADMIN, is_active=True
    )
    db.add(admin)
    
    # Seed technician
    tech = User(
        id=uuid.uuid4(), tenant_id=t.id, email=f"tech@{slug}.com",
        full_name="Technician User", hashed_password=hash_password("Pass@1234"),
        role=TenantRole.TECHNICIAN, is_active=True
    )
    db.add(tech)
    
    await db.flush()
    return t, admin, tech

async def _login(client, slug, email):
    r = await client.post("/api/v1/auth/login", json={
        "email": email, "password": "Pass@1234", "tenant_slug": slug
    })
    assert r.status_code == 200
    return r.json()["access_token"]

@pytest.mark.asyncio
async def test_multi_company_cash_flow_e2e(client, db):
    # 1. Seed tenant, admin, technician
    tenant, admin, tech = await _seed_tenant_admin_and_tech(db, "e2e-cash-co")
    
    # Login both admin and tech
    admin_token = await _login(client, tenant.slug, admin.email)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    tech_token = await _login(client, tenant.slug, tech.email)
    tech_headers = {"Authorization": f"Bearer {tech_token}"}
    
    # 2. Create Company (Admin)
    r_company = await client.post("/api/v1/companies", json={
        "name": "E2E India Pvt Ltd",
        "gst_status": "GST",
        "gstin": "27ABCDE1234F1Z5",
        "address": "456 Corporate Towers, Pune",
        "contact_details": {"phone": "9876543210", "email": "finance@e2eindia.com"},
        "bank_details": {"bank_name": "HDFC Bank", "account_number": "50100012345678"},
        "authorized_signatory": {"name": "Signatory Officer"},
        "is_default": True
    }, headers=admin_headers)
    assert r_company.status_code == 201
    company_id = r_company.json()["id"]
    
    # 3. Create Custom Company Template (Admin)
    r_template = await client.post("/api/v1/company-templates", json={
        "company_id": company_id,
        "document_type": "TAX_INVOICE",
        "template_html": "<html><body>E2E Invoice #{{ doc.invoice_number }} for {{ company.name }}</body></html>",
        "is_active": True
    }, headers=admin_headers)
    assert r_template.status_code == 200
    
    # 4. Create Customer (Admin)
    r_customer = await client.post("/api/v1/customers", json={
        "name": "E2E Retail Customer",
        "category": "commercial"
    }, headers=admin_headers)
    assert r_customer.status_code == 201
    customer_id = r_customer.json()["id"]
    
    # 5. Create Service Ticket and Assign to Technician (Admin)
    r_ticket = await client.post("/api/v1/service-tickets", json={
        "customer_id": customer_id,
        "complaint": "Camera feedback is distorted",
        "priority": "high"
    }, headers=admin_headers)
    assert r_ticket.status_code == 201
    ticket_id = r_ticket.json()["id"]
    
    r_assign = await client.patch(f"/api/v1/service-tickets/{ticket_id}", json={
        "assigned_to": str(tech.id),
        "status": "assigned"
    }, headers=admin_headers)
    assert r_assign.status_code == 200
    
    # 6. Log Cash Collection (Technician)
    r_cash = await client.post("/api/v1/cash-collections", json={
        "customer_name": "E2E Retail Customer",
        "company_id": company_id,
        "service_ticket_id": ticket_id,
        "amount": 2500.0,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "remarks": "Collected offline payment from customer site"
    }, headers=tech_headers)
    assert r_cash.status_code == 201
    cash_id = r_cash.json()["id"]
    assert r_cash.json()["status"] == "pending"
    
    # 7. Check Cash Collections List (Admin vs Technician)
    # Admin sees all collections
    r_admin_list = await client.get("/api/v1/cash-collections", headers=admin_headers)
    assert r_admin_list.status_code == 200
    admin_list = r_admin_list.json()
    assert any(c["id"] == cash_id for c in admin_list)
    
    # Tech sees only their own
    r_tech_list = await client.get("/api/v1/cash-collections", headers=tech_headers)
    assert r_tech_list.status_code == 200
    tech_list = r_tech_list.json()
    assert any(c["id"] == cash_id for c in tech_list)
    
    # 8. Approve Cash Collection (Admin)
    r_verify = await client.post(f"/api/v1/cash-collections/{cash_id}/action", json={
        "action": "APPROVED",
        "notes": "Verified amount deposited in safe"
    }, headers=admin_headers)
    assert r_verify.status_code == 200
    assert r_verify.json()["status"] == "received"
    assert len(r_verify.json()["logs"]) == 1
    assert r_verify.json()["logs"][0]["action"] == "APPROVED"
    assert r_verify.json()["logs"][0]["notes"] == "Verified amount deposited in safe"
