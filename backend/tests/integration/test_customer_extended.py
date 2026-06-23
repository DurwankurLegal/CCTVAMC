"""Customer contacts, interaction history (SRS 4.3) and document upload (4.17/4.18)."""
import io
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_contacts_history_and_documents(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    cust = await client.post(
        "/api/v1/customers",
        json={"name": "Acme Commercial", "category": "commercial", "status": "active"},
        headers=headers,
    )
    assert cust.status_code == 201
    cid = cust.json()["id"]
    assert cust.json()["status"] == "active"

    # multiple contacts with roles
    for role in ("admin", "accounts", "technical"):
        r = await client.post(
            f"/api/v1/customers/{cid}/contacts",
            json={"name": f"{role} person", "role": role, "email": f"{role}@acme.com"},
            headers=headers,
        )
        assert r.status_code == 201
    contacts = await client.get(f"/api/v1/customers/{cid}/contacts", headers=headers)
    assert len(contacts.json()) == 3

    # interaction history aggregates (empty but well-formed)
    hist = await client.get(f"/api/v1/customers/{cid}/history", headers=headers)
    assert hist.status_code == 200
    assert set(hist.json().keys()) == {"leads", "tickets", "invoices", "quotations"}

    # document upload (storage unconfigured in tests -> synthetic url)
    files = {"file": ("warranty.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")}
    data = {"entity_type": "customer", "entity_id": cid, "doc_type": "warranty_card"}
    up = await client.post("/api/v1/documents", files=files, data=data, headers=headers)
    assert up.status_code == 201
    assert up.json()["url"]

    listed = await client.get(
        f"/api/v1/documents?entity_type=customer&entity_id={cid}", headers=headers
    )
    assert len(listed.json()) == 1
