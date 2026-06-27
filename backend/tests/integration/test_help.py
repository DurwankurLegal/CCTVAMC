from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from uuid import uuid4
from app.models.help import HelpCategory, HelpArticle, HelpFAQ, HelpFeedback, HelpBookmark
from app.models.subscription import Module, SaasPlan, TenantSubscription, TenantModule
from app.models.tenant import Tenant
from app.models.user import User, TenantRole
from app.core.security import hash_password, create_access_token

async def seed_test_help_metadata(db):
    """Seed modules, categories, articles, and FAQs dynamically inside test transactions."""
    # Seed Modules
    modules = {}
    for code in ["sales", "rental", "amc", "inventory", "assets"]:
        m = Module(code=code, name=code.upper(), is_active=True)
        db.add(m)
        modules[code] = m
    
    # Seed SaaS Plan
    p = SaasPlan(code="growth", name="Growth", is_active=True)
    db.add(p)
    
    # Seed Help Categories
    cat_gs = HelpCategory(name="Getting Started", slug="getting-started", display_order=1)
    cat_crm = HelpCategory(name="CRM", slug="crm", display_order=2)
    cat_sales = HelpCategory(name="Sales", slug="sales", display_order=3)
    cat_rental = HelpCategory(name="Rental", slug="rental", display_order=4)
    cat_amc = HelpCategory(name="AMC", slug="amc", display_order=5)
    db.add_all([cat_gs, cat_crm, cat_sales, cat_rental, cat_amc])
    await db.flush()

    # Seed Help Articles
    art_intro = HelpArticle(
        category_id=cat_gs.id, title="Introduction to CCTV ERP", slug="introduction",
        purpose="Intro test", content_markdown="Welcome to the help center...",
        applicable_module="core", status="published", is_active=True
    )
    art_leads = HelpArticle(
        category_id=cat_crm.id, title="Leads Guide", slug="lead-management",
        purpose="Leads test", content_markdown="Leads details...",
        applicable_module="core", status="published", is_active=True
    )
    art_quotes = HelpArticle(
        category_id=cat_sales.id, title="Quotations Guide", slug="quotations",
        purpose="Quotations test", content_markdown="Quotations details...",
        applicable_module="sales", status="published", is_active=True
    )
    art_rentals = HelpArticle(
        category_id=cat_rental.id, title="Rental Contracts Guide", slug="rental-contracts",
        purpose="Rental test", content_markdown="Rental details...",
        applicable_module="rental", status="published", is_active=True
    )
    art_amc = HelpArticle(
        category_id=cat_amc.id, title="AMC Contracts Guide", slug="amc-contracts",
        purpose="AMC test", content_markdown="AMC details...",
        applicable_module="amc", status="published", is_active=True
    )
    db.add_all([art_intro, art_leads, art_quotes, art_rentals, art_amc])
    await db.flush()

    # Seed FAQs
    faq_1 = HelpFAQ(article_id=art_intro.id, question="What is core access?", answer="Core is always visible.", display_order=1)
    db.add(faq_1)
    await db.flush()


async def setup_test_tenant(db, slug: str, active_modules: list[str]) -> tuple[Tenant, User, str]:
    """Helper to provision a tenant, set dynamic active modules, and create a user token."""
    tenant = Tenant(name=slug.capitalize(), slug=slug)
    db.add(tenant)
    await db.flush()

    # Add active modules
    for m_code in active_modules:
        db.add(TenantModule(tenant_id=tenant.id, module_code=m_code, status="active", starts_at=datetime.now(timezone.utc)))
    await db.flush()

    user = User(
        tenant_id=tenant.id,
        email=f"admin@{slug}.com",
        full_name=f"Admin {slug.upper()}",
        hashed_password=hash_password("password123"),
        role=TenantRole.ADMIN
    )
    db.add(user)
    await db.flush()

    token = create_access_token({
        "sub": str(user.id),
        "tenant_id": str(tenant.id),
        "role": user.role,
        "is_platform_admin": False,
        "type": "access"
    })
    return tenant, user, token


@pytest.mark.asyncio
async def test_help_menu_module_filtering_company_a(client: AsyncClient, db):
    """
    Company A has Sales only. Verify their help center menu hides Rental and AMC.
    """
    await seed_test_help_metadata(db)
    tenant, user, token = await setup_test_tenant(db, "company-a", ["sales"])
    headers = {"Authorization": f"Bearer {token}"}

    # Get Menu
    menu_res = await client.get("/api/v1/help/menu", headers=headers)
    assert menu_res.status_code == 200
    menu = menu_res.json()
    
    # Assert Getting Started, CRM, and Sales are visible
    categories = [cat["slug"] for cat in menu]
    assert "getting-started" in categories
    assert "crm" in categories
    assert "sales" in categories
    
    # Assert Rental and AMC categories are hidden
    assert "rental" not in categories
    assert "amc" not in categories


@pytest.mark.asyncio
async def test_help_menu_module_filtering_company_c(client: AsyncClient, db):
    """
    Company C has AMC only. Verify their help center menu hides Sales and Rental.
    """
    await seed_test_help_metadata(db)
    tenant, user, token = await setup_test_tenant(db, "company-c", ["amc"])
    headers = {"Authorization": f"Bearer {token}"}

    # Get Menu
    menu_res = await client.get("/api/v1/help/menu", headers=headers)
    assert menu_res.status_code == 200
    menu = menu_res.json()
    
    categories = [cat["slug"] for cat in menu]
    assert "getting-started" in categories
    assert "crm" in categories
    assert "amc" in categories
    
    assert "sales" not in categories
    assert "rental" not in categories


@pytest.mark.asyncio
async def test_help_article_access_gating(client: AsyncClient, db):
    """
    Verify that direct requests to unsubscribed module articles return 402.
    """
    await seed_test_help_metadata(db)
    tenant, user, token = await setup_test_tenant(db, "company-a", ["sales"])
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Access Quotations (Sales - Subscribed) -> Should work
    quote_res = await client.get("/api/v1/help/articles/quotations", headers=headers)
    assert quote_res.status_code == 200
    assert quote_res.json()["slug"] == "quotations"

    # 2. Access Rental (Unsubscribed) -> Should return 402
    rental_res = await client.get("/api/v1/help/articles/rental-contracts", headers=headers)
    assert rental_res.status_code == 402
    assert "requires" in rental_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_help_search_filtering(client: AsyncClient, db):
    """
    Verify search results display matching snippets and filter out unsubscribed modules.
    """
    await seed_test_help_metadata(db)
    tenant, user, token = await setup_test_tenant(db, "company-a", ["sales"])
    headers = {"Authorization": f"Bearer {token}"}

    # Search for Quotation -> Should find sales quotes
    search_res = await client.get("/api/v1/help/search?q=quotation", headers=headers)
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) > 0
    assert any("quotations" in r["slug"] for r in results)

    # Search for Rental -> Should filter out because Company A is not subscribed
    search_rent = await client.get("/api/v1/help/search?q=rental", headers=headers)
    assert search_rent.status_code == 200
    rent_results = search_rent.json()
    assert len(rent_results) == 0


@pytest.mark.asyncio
async def test_help_feedback_and_bookmarks(client: AsyncClient, db):
    """
    Verify bookmarks toggling, list bookmarks, and rating feedback logging.
    """
    await seed_test_help_metadata(db)
    tenant, user, token = await setup_test_tenant(db, "company-e", ["sales", "rental", "amc"])
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Get introduction article
    intro_res = await client.get("/api/v1/help/articles/introduction", headers=headers)
    assert intro_res.status_code == 200
    art_id = intro_res.json()["id"]

    # 2. Toggle Bookmark
    bk_res = await client.post(f"/api/v1/help/articles/{art_id}/bookmark", headers=headers)
    assert bk_res.status_code == 200
    assert bk_res.json()["bookmarked"] is True

    # 3. List Bookmarks
    list_res = await client.get("/api/v1/help/bookmarks", headers=headers)
    assert list_res.status_code == 200
    assert any(b["slug"] == "introduction" for b in list_res.json())

    # 4. Submit Feedback
    feed_res = await client.post(
        f"/api/v1/help/articles/{art_id}/feedback", 
        json={
            "rating": 5,
            "comments": "Super clean explanation! Extremely helpful.",
            "is_outdated": False
        },
        headers=headers
    )
    assert feed_res.status_code == 201
    assert feed_res.json()["comments"] == "Super clean explanation! Extremely helpful."
