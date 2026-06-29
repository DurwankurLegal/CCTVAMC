import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import HTTPException, status
from app.services.company_template import render_company_document, get_template_by_type
from app.models.company import Company
from app.models.company_template import CompanyTemplate

@pytest.mark.asyncio
async def test_get_template_by_type_query():
    # Mock AsyncSession and its execute method
    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_res
    
    tenant_id = uuid4()
    company_id = uuid4()
    
    with patch("app.services.company_template.CompanyTemplateRepository") as MockRepo:
        mock_repo_inst = AsyncMock()
        MockRepo.return_value = mock_repo_inst
        
        res = await get_template_by_type(db, tenant_id, company_id, "TAX_INVOICE")
        
        # Check repository and context setting
        MockRepo.assert_called_once_with(db, tenant_id)
        mock_repo_inst._set_rls_context.assert_called_once()
        db.execute.assert_called_once()
        assert res is None

@pytest.mark.asyncio
@patch("app.services.company_template.get_tenant")
@patch("app.services.company_template.HTML")
@patch("app.services.company_template.get_template_by_type")
@patch("app.services.company_template.TenantRepository")
async def test_render_company_document_success_default_template(
    MockTenantRepository, mock_get_template_by_type, MockHTML, mock_get_tenant,
):
    db = AsyncMock()
    tenant_id = uuid4()
    company_id = uuid4()
    
    mock_tenant = MagicMock()
    mock_tenant.settings = {}
    mock_tenant.branding = {}
    mock_tenant.registered_address = ""
    mock_get_tenant.return_value = mock_tenant
    
    # Mock company object
    company = Company(
        id=company_id,
        tenant_id=tenant_id,
        name="Acme Solutions",
        gst_status="GST",
        gstin="27ABCDE1234F1Z5",
        address="123 Street",
        contact_details={"phone": "12345", "email": "acme@test.com"},
        bank_details={"bank_name": "Test Bank", "account_number": "98765"},
        authorized_signatory={"name": "Manager"},
        logo_url="http://logo.url"
    )
    
    # Setup company repo mock
    mock_company_repo = AsyncMock()
    mock_company_repo.get.return_value = company
    
    mock_subscribed = MagicMock(return_value=mock_company_repo)
    MockTenantRepository.__getitem__.return_value = mock_subscribed
    
    # Setup template override mock (no override -> None)
    mock_get_template_by_type.return_value = None
    
    # Setup HTML/WeasyPrint mock
    mock_html_inst = MagicMock()
    mock_html_inst.write_pdf.return_value = b"%PDF-mock-bytes"
    MockHTML.return_value = mock_html_inst
    
    context = {
        "customer": {"name": "Customer A", "address": "Road 1"},
        "doc": {
            "invoice_number": "INV-100",
            "invoice_date": "2026-06-26",
            "subtotal": 1000.0,
            "total_amount": 1180.0,
            "cgst_amount": 90.0,
            "sgst_amount": 90.0,
        },
        "items": [{"description": "Service C", "quantity": 1, "unit_price": 1000.0, "amount": 1000.0}]
    }
    
    pdf_bytes = await render_company_document(db, tenant_id, company_id, "TAX_INVOICE", context)
    
    assert pdf_bytes == b"%PDF-mock-bytes"
    mock_company_repo.get.assert_called_once_with(company_id)
    mock_get_template_by_type.assert_called_once_with(db, tenant_id, company_id, "TAX_INVOICE")
    MockHTML.assert_called_once()
    mock_html_inst.write_pdf.assert_called_once()

@pytest.mark.asyncio
@patch("app.services.company_template.get_tenant")
@patch("app.services.company_template.HTML")
@patch("app.services.company_template.get_template_by_type")
@patch("app.services.company_template.TenantRepository")
async def test_render_company_document_success_custom_template(
    MockTenantRepository, mock_get_template_by_type, MockHTML, mock_get_tenant,
):
    db = AsyncMock()
    tenant_id = uuid4()
    company_id = uuid4()
    
    mock_tenant = MagicMock()
    mock_tenant.settings = {}
    mock_tenant.branding = {}
    mock_tenant.registered_address = ""
    mock_get_tenant.return_value = mock_tenant
    
    company = Company(
        id=company_id,
        tenant_id=tenant_id,
        name="Acme Solutions",
        gst_status="GST",
        contact_details={},
        bank_details={},
    )
    
    mock_company_repo = AsyncMock()
    mock_company_repo.get.return_value = company
    
    mock_subscribed = MagicMock(return_value=mock_company_repo)
    MockTenantRepository.__getitem__.return_value = mock_subscribed
    
    # Custom template override
    custom_template = CompanyTemplate(
        id=uuid4(),
        company_id=company_id,
        document_type="TAX_INVOICE",
        template_html="<html><body>CUSTOM INVOICE {{ company.name }} - {{ doc.invoice_number }}</body></html>",
        is_active=True
    )
    mock_get_template_by_type.return_value = custom_template
    
    mock_html_inst = MagicMock()
    mock_html_inst.write_pdf.return_value = b"%PDF-custom-mock-bytes"
    MockHTML.return_value = mock_html_inst
    
    context = {"doc": {"invoice_number": "INV-CUSTOM-999"}, "items": []}
    
    pdf_bytes = await render_company_document(db, tenant_id, company_id, "TAX_INVOICE", context)
    
    assert pdf_bytes == b"%PDF-custom-mock-bytes"
    # Verify Jinja render call
    called_html_kwargs = MockHTML.call_args[1]
    assert "string" in called_html_kwargs
    assert "CUSTOM INVOICE Acme Solutions - INV-CUSTOM-999" in called_html_kwargs["string"]

@pytest.mark.asyncio
@patch("app.services.company_template.TenantRepository")
async def test_render_company_document_company_not_found(MockTenantRepository):
    db = AsyncMock()
    tenant_id = uuid4()
    company_id = uuid4()
    
    mock_company_repo = AsyncMock()
    mock_company_repo.get.return_value = None
    
    mock_subscribed = MagicMock(return_value=mock_company_repo)
    MockTenantRepository.__getitem__.return_value = mock_subscribed
    
    with pytest.raises(HTTPException) as exc_info:
        await render_company_document(db, tenant_id, company_id, "TAX_INVOICE", {})
        
    assert exc_info.value.status_code == 404
    assert "Company not found" in exc_info.value.detail

@pytest.mark.asyncio
@patch("app.services.company_template.get_tenant")
@patch("app.services.company_template.get_template_by_type")
@patch("app.services.company_template.TenantRepository")
async def test_render_company_document_unsupported_type(
    MockTenantRepository, mock_get_template_by_type, mock_get_tenant
):
    db = AsyncMock()
    tenant_id = uuid4()
    company_id = uuid4()
    
    mock_tenant = MagicMock()
    mock_tenant.settings = {}
    mock_tenant.branding = {}
    mock_tenant.registered_address = ""
    mock_get_tenant.return_value = mock_tenant
    
    company = Company(id=company_id, tenant_id=tenant_id, name="Acme Solutions", gst_status="GST", contact_details={}, bank_details={})
    mock_company_repo = AsyncMock()
    mock_company_repo.get.return_value = company
    
    mock_subscribed = MagicMock(return_value=mock_company_repo)
    MockTenantRepository.__getitem__.return_value = mock_subscribed
    
    mock_get_template_by_type.return_value = None
    
    # Try to render an unsupported document type
    with pytest.raises(HTTPException) as exc_info:
        await render_company_document(db, tenant_id, company_id, "INVALID_DOC_TYPE", {})
        
    assert exc_info.value.status_code == 500
    assert "could not be resolved" in exc_info.value.detail
