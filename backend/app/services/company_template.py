from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.company_template import CompanyTemplate
from app.models.company import Company
from app.repositories.base import TenantRepository
from app.services.crud_base import make_crud
from app.schemas.company_template import CompanyTemplateCreate, CompanyTemplateUpdate


class CompanyTemplateRepository(TenantRepository[CompanyTemplate]):
    model = CompanyTemplate

list_templates, get_template, create_template, update_template = make_crud(CompanyTemplateRepository, CompanyTemplate)

async def get_template_by_type(db: AsyncSession, tenant_id: UUID, company_id: UUID, document_type: str) -> CompanyTemplate:
    repo = CompanyTemplateRepository(db, tenant_id)
    await repo._set_rls_context()
    stmt = select(CompanyTemplate).where(
        CompanyTemplate.tenant_id == tenant_id,
        CompanyTemplate.company_id == company_id,
        CompanyTemplate.document_type == document_type,
        CompanyTemplate.is_active == True
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

# Default HTML structures for fallback dynamic rendering
DEFAULT_HTML_TEMPLATES = {
    "TAX_INVOICE": """
    <html>
    <head>
      <style>
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; margin: 0; padding: 20px; font-size: 12px; }
        .header { display: flex; justify-content: space-between; border-bottom: 2px solid #0F2A43; padding-bottom: 10px; margin-bottom: 20px; }
        .logo { max-height: 60px; }
        .company-details { text-align: right; }
        .title { font-size: 20px; color: #0F2A43; font-weight: bold; margin-top: 0; }
        .meta-table, .items-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        .meta-table td { padding: 4px 0; vertical-align: top; }
        .items-table th { background-color: #0F2A43; color: white; padding: 8px; text-align: left; }
        .items-table td { border-bottom: 1px solid #ddd; padding: 8px; }
        .totals { width: 40%; margin-left: 60%; margin-top: 20px; border-collapse: collapse; }
        .totals td { padding: 6px; border-bottom: 1px solid #eee; }
        .totals .grand-total { font-weight: bold; font-size: 14px; border-bottom: 2px solid #0F2A43; }
        .footer { margin-top: 50px; border-top: 1px solid #ccc; padding-top: 10px; font-size: 10px; text-align: center; color: #777; }
        .bank-details { margin-top: 20px; background-color: #f9f9f9; padding: 10px; border-radius: 4px; border: 1px solid #eee; }
        .signature-box { text-align: right; margin-top: 30px; }
        .signature-img { max-height: 40px; margin-top: 5px; }
      </style>
    </head>
    <body>
      <div class="header">
        <div>
          {% if company.logo_url %}
            <img class="logo" src="{{ company.logo_url }}" alt="Logo" />
          {% else %}
            <h2>{{ company.name }}</h2>
          {% endif %}
        </div>
        <div class="company-details">
          <div class="title">TAX INVOICE</div>
          <div><strong>{{ company.name }}</strong></div>
          <div>{{ company.address or '' }}</div>
          {% if company.gstin %}<div>GSTIN: {{ company.gstin }}</div>{% endif %}
          <div>Email: {{ company.contact_details.get('email', '') }} | Phone: {{ company.contact_details.get('phone', '') }}</div>
        </div>
      </div>

      <table class="meta-table">
        <tr>
          <td style="width: 50%;">
            <strong>Billed To:</strong><br/>
            {{ customer.name }}<br/>
            {{ customer.address or '' }}<br/>
            {% if customer.phone %}Phone: {{ customer.phone }}<br/>{% endif %}
            {% if customer.gstin %}GSTIN: {{ customer.gstin }}{% endif %}
          </td>
          <td style="width: 50%; text-align: right;">
            <strong>Invoice No:</strong> {{ doc.invoice_number }}<br/>
            <strong>Date:</strong> {{ doc.invoice_date }}<br/>
            {% if doc.due_date %}<strong>Due Date:</strong> {{ doc.due_date }}<br/>{% endif %}
            {% if doc.supply_state_code %}<strong>Place of Supply Code:</strong> {{ doc.supply_state_code }}{% endif %}
          </td>
        </tr>
      </table>

      <table class="items-table">
        <thead>
          <tr>
            <th>Description</th>
            <th style="text-align: right; width: 10%;">Qty</th>
            <th style="text-align: right; width: 15%;">Unit Price</th>
            <th style="text-align: right; width: 15%;">Amount</th>
          </tr>
        </thead>
        <tbody>
          {% for item in items %}
          <tr>
            <td>{{ item.get('description', '') }}</td>
            <td style="text-align: right;">{{ item.get('quantity', '') }}</td>
            <td style="text-align: right;">{{ item.get('unit_price', '') }}</td>
            <td style="text-align: right;">{{ item.get('amount', '') }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>

      <table class="totals">
        <tr>
          <td>Subtotal</td>
          <td style="text-align: right;">{{ doc.subtotal }}</td>
        </tr>
        {% if doc.cgst_amount %}
        <tr>
          <td>CGST</td>
          <td style="text-align: right;">{{ doc.cgst_amount }}</td>
        </tr>
        {% endif %}
        {% if doc.sgst_amount %}
        <tr>
          <td>SGST</td>
          <td style="text-align: right;">{{ doc.sgst_amount }}</td>
        </tr>
        {% endif %}
        {% if doc.igst_amount %}
        <tr>
          <td>IGST</td>
          <td style="text-align: right;">{{ doc.igst_amount }}</td>
        </tr>
        {% endif %}
        <tr class="grand-total">
          <td>Total</td>
          <td style="text-align: right;">{{ doc.total_amount }}</td>
        </tr>
      </table>

      <div class="bank-details">
        <strong>Bank Details:</strong><br/>
        Bank Name: {{ company.bank_details.get('bank_name', '') }} | 
        A/C Name: {{ company.bank_details.get('beneficiary_name', company.name) }}<br/>
        A/C No: {{ company.bank_details.get('account_number', '') }} | 
        IFSC: {{ company.bank_details.get('ifsc_code', '') }} | 
        Branch: {{ company.bank_details.get('branch', '') }}
      </div>

      {% if company.authorized_signatory and company.authorized_signatory.get('name') %}
      <div class="signature-box" style="text-align: right; margin-top: 30px; position: relative;">
        <div>For <strong>{{ company.name }}</strong></div>
        <div style="position: relative; display: inline-block; height: 50px; margin: 5px 0;">
          {% if company.authorized_signatory.get('signature_url') %}
            <img class="signature-img" src="{{ company.authorized_signatory.get('signature_url') }}" style="max-height: 40px; position: relative; z-index: 2;" />
          {% endif %}
          {% if company.seal_url %}
            <img class="seal-img" src="{{ company.seal_url }}" style="max-height: 50px; position: absolute; right: 10px; top: -5px; opacity: 0.85; z-index: 1;" />
          {% endif %}
        </div>
        <div>Authorized Signatory ({{ company.authorized_signatory.get('name') }})</div>
      </div>
      {% endif %}

      <div class="footer">
        Thank you for your business. For any queries, please email {{ company.contact_details.get('email', '') }}
      </div>
    </body>
    </html>
    """,
    "NON_GST_INVOICE": """
    <html>
    <head>
      <style>
        body { font-family: Arial, sans-serif; color: #333; padding: 20px; font-size: 12px; }
        .header { display: flex; justify-content: space-between; border-bottom: 2px solid #555; padding-bottom: 10px; margin-bottom: 20px; }
        .logo { max-height: 60px; }
        .title { font-size: 20px; color: #333; font-weight: bold; margin-top: 0; }
        .meta-table, .items-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        .items-table th { background-color: #555; color: white; padding: 8px; text-align: left; }
        .items-table td { border-bottom: 1px solid #ddd; padding: 8px; }
        .totals { width: 40%; margin-left: 60%; margin-top: 20px; border-collapse: collapse; }
        .totals td { padding: 6px; border-bottom: 1px solid #eee; }
        .totals .grand-total { font-weight: bold; font-size: 14px; border-bottom: 2px solid #555; }
        .footer { margin-top: 50px; text-align: center; color: #777; font-size: 10px; }
      </style>
    </head>
    <body>
      <div class="header">
        <div>
          {% if company.logo_url %}
            <img class="logo" src="{{ company.logo_url }}" />
          {% else %}
            <h2>{{ company.name }}</h2>
          {% endif %}
        </div>
        <div style="text-align: right;">
          <div class="title">INVOICE (Non-GST)</div>
          <div><strong>{{ company.name }}</strong></div>
          <div>{{ company.address or '' }}</div>
        </div>
      </div>

      <table class="meta-table">
        <tr>
          <td>
            <strong>Billed To:</strong><br/>
            {{ customer.name }}<br/>
            {{ customer.address or '' }}
          </td>
          <td style="text-align: right;">
            <strong>Invoice No:</strong> {{ doc.invoice_number }}<br/>
            <strong>Date:</strong> {{ doc.invoice_date }}<br/>
          </td>
        </tr>
      </table>

      <table class="items-table">
        <thead>
          <tr>
            <th>Description</th>
            <th style="text-align: right; width: 10%;">Qty</th>
            <th style="text-align: right; width: 15%;">Unit Price</th>
            <th style="text-align: right; width: 15%;">Amount</th>
          </tr>
        </thead>
        <tbody>
          {% for item in items %}
          <tr>
            <td>{{ item.get('description', '') }}</td>
            <td style="text-align: right;">{{ item.get('quantity', '') }}</td>
            <td style="text-align: right;">{{ item.get('unit_price', '') }}</td>
            <td style="text-align: right;">{{ item.get('amount', '') }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>

      <table class="totals">
        <tr class="grand-total">
          <td>Total Amount</td>
          <td style="text-align: right;">{{ doc.total_amount }}</td>
        </tr>
      </table>

      <div class="footer">
        This is a non-GST invoice issued by {{ company.name }}.
      </div>
    </body>
    </html>
    """,
    "QUOTATION": """
    <html>
    <head>
      <style>
        body { font-family: 'Helvetica Neue', Arial, sans-serif; color: #333; padding: 20px; font-size: 12px; }
        .header { display: flex; justify-content: space-between; border-bottom: 2px solid #0F2A43; padding-bottom: 10px; margin-bottom: 20px; }
        .logo { max-height: 60px; }
        .title { font-size: 20px; color: #0F2A43; font-weight: bold; margin-top: 0; }
        .meta-table, .items-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        .items-table th { background-color: #0F2A43; color: white; padding: 8px; text-align: left; }
        .items-table td { border-bottom: 1px solid #ddd; padding: 8px; }
        .totals { width: 40%; margin-left: 60%; border-collapse: collapse; }
        .totals td { padding: 6px; border-bottom: 1px solid #eee; }
        .totals .grand-total { font-weight: bold; font-size: 14px; border-bottom: 2px solid #0F2A43; }
        .terms { margin-top: 30px; font-size: 11px; padding: 10px; background-color: #f9f9f9; border-left: 3px solid #0F2A43; }
      </style>
    </head>
    <body>
      <div class="header">
        <div>
          {% if company.logo_url %}
            <img class="logo" src="{{ company.logo_url }}" />
          {% else %}
            <h2>{{ company.name }}</h2>
          {% endif %}
        </div>
        <div style="text-align: right;">
          <div class="title">QUOTATION</div>
          <div><strong>{{ company.name }}</strong></div>
          <div>{{ company.address or '' }}</div>
        </div>
      </div>

      <table class="meta-table">
        <tr>
          <td>
            <strong>Prepared For:</strong><br/>
            {{ customer.name }}<br/>
            {{ customer.address or '' }}
          </td>
          <td style="text-align: right;">
            <strong>Quotation No:</strong> {{ doc.quotation_number }}<br/>
            <strong>Date:</strong> {{ doc.created_at.strftime('%Y-%m-%d') if doc.created_at else '' }}<br/>
            {% if doc.valid_until %}<strong>Valid Until:</strong> {{ doc.valid_until }}<br/>{% endif %}
          </td>
        </tr>
      </table>

      <table class="items-table">
        <thead>
          <tr>
            <th>Description</th>
            <th style="text-align: right; width: 10%;">Qty</th>
            <th style="text-align: right; width: 15%;">Unit Price</th>
            <th style="text-align: right; width: 15%;">Amount</th>
          </tr>
        </thead>
        <tbody>
          {% for item in items %}
          <tr>
            <td>{{ item.get('description', '') }}</td>
            <td style="text-align: right;">{{ item.get('quantity', '') }}</td>
            <td style="text-align: right;">{{ item.get('unit_price', '') }}</td>
            <td style="text-align: right;">{{ item.get('amount', '') }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>

      <table class="totals">
        <tr>
          <td>Subtotal</td>
          <td style="text-align: right;">{{ doc.subtotal }}</td>
        </tr>
        {% if doc.cgst_amount %}
        <tr>
          <td>CGST</td>
          <td style="text-align: right;">{{ doc.cgst_amount }}</td>
        </tr>
        {% endif %}
        {% if doc.sgst_amount %}
        <tr>
          <td>SGST</td>
          <td style="text-align: right;">{{ doc.sgst_amount }}</td>
        </tr>
        {% endif %}
        {% if doc.igst_amount %}
        <tr>
          <td>IGST</td>
          <td style="text-align: right;">{{ doc.igst_amount }}</td>
        </tr>
        {% endif %}
        <tr class="grand-total">
          <td>Total Quote</td>
          <td style="text-align: right;">{{ doc.total_amount }}</td>
        </tr>
      </table>

      <div class="bank-details" style="margin-top: 20px; background-color: #f9f9f9; padding: 10px; border-radius: 4px; border: 1px solid #eee; font-size: 11px;">
        <strong>Bank Details:</strong><br/>
        Bank Name: {{ company.bank_details.get('bank_name', '') }} | 
        A/C Name: {{ company.bank_details.get('beneficiary_name', company.name) }}<br/>
        A/C No: {{ company.bank_details.get('account_number', '') }} | 
        IFSC: {{ company.bank_details.get('ifsc_code', '') }} | 
        Branch: {{ company.bank_details.get('branch', '') }}
        {% if company.bank_details.get('upi_id') %}
          | UPI ID: {{ company.bank_details.get('upi_id') }}
        {% endif %}
      </div>

      <table style="width: 100%; margin-top: 30px; border: none; border-collapse: collapse;">
        <tr>
          <td style="width: 50%; vertical-align: top; border: none; padding: 0;">
            {% if doc.terms %}
            <div class="terms" style="margin-top: 0; font-size: 11px; padding: 10px; background-color: #f9f9f9; border-left: 3px solid #0F2A43;">
              <strong>Terms & Conditions:</strong><br/>
              {{ doc.terms | safe }}
            </div>
            {% endif %}
          </td>
          <td style="width: 50%; text-align: right; vertical-align: top; border: none; padding: 0;">
            {% if company.authorized_signatory and company.authorized_signatory.get('name') %}
            <div class="signature-box" style="position: relative; display: inline-block; min-height: 80px; text-align: right;">
              <div>For <strong>{{ company.name }}</strong></div>
              <div style="position: relative; display: inline-block; height: 50px; margin: 5px 0;">
                {% if company.authorized_signatory.get('signature_url') %}
                  <img class="signature-img" src="{{ company.authorized_signatory.get('signature_url') }}" style="max-height: 40px; position: relative; z-index: 2;" />
                {% endif %}
                {% if company.seal_url %}
                  <img class="seal-img" src="{{ company.seal_url }}" style="max-height: 50px; position: absolute; right: 10px; top: -5px; opacity: 0.85; z-index: 1;" />
                {% endif %}
              </div>
              <div>Authorized Signatory ({{ company.authorized_signatory.get('name') }})</div>
            </div>
            {% endif %}
          </td>
        </tr>
      </table>
    </body>
    </html>
    """,
    "PAYMENT_RECEIPT": """
    <html>
    <head>
      <style>
        body { font-family: sans-serif; padding: 20px; font-size: 13px; color: #333; }
        .receipt-card { border: 1px solid #ccc; border-radius: 8px; padding: 20px; max-width: 500px; margin: 0 auto; }
        .logo { max-height: 40px; margin-bottom: 10px; }
        .header { text-align: center; border-bottom: 1px solid #eee; padding-bottom: 15px; margin-bottom: 15px; }
        .title { font-size: 18px; font-weight: bold; color: #2e7d32; }
        .details-table { width: 100%; margin-bottom: 20px; }
        .details-table td { padding: 6px; }
        .details-table td:first-child { font-weight: bold; color: #555; }
        .footer { text-align: center; font-size: 11px; color: #888; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px; }
      </style>
    </head>
    <body>
      <div class="receipt-card">
        <div class="header">
          {% if company.logo_url %}
            <img class="logo" src="{{ company.logo_url }}" /><br/>
          {% endif %}
          <div class="title">PAYMENT RECEIPT</div>
          <div>{{ company.name }}</div>
        </div>

        <table class="details-table">
          <tr>
            <td>Receipt For:</td>
            <td>Invoice No. {{ doc.invoice.invoice_number if doc.invoice else doc.invoice_id }}</td>
          </tr>
          <tr>
            <td>Amount Paid:</td>
            <td style="font-size: 15px; font-weight: bold; color: #2e7d32;">INR {{ doc.amount }}</td>
          </tr>
          <tr>
            <td>Payment Date:</td>
            <td>{{ doc.payment_date or '' }}</td>
          </tr>
          <tr>
            <td>Payment Method:</td>
            <td>{{ doc.method or 'CASH' }}</td>
          </tr>
          {% if doc.reference %}
          <tr>
            <td>Transaction Ref:</td>
            <td>{{ doc.reference }}</td>
          </tr>
          {% endif %}
        </table>

        <div class="footer">
          Thank you for your payment. For inquiries, contact {{ company.contact_details.get('email', '') }}
        </div>
      </div>
    </body>
    </html>
    """
}

async def render_company_document(
    db: AsyncSession,
    tenant_id: UUID,
    company_id: UUID,
    document_type: str,
    context: dict
) -> bytes:
    # 1. Fetch Company details
    company_repo = TenantRepository[Company](db, tenant_id)
    company_repo.model = Company
    company = await company_repo.get(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    from app.services.tenant import get_tenant
    tenant = await get_tenant(db, tenant_id)
    t_settings = tenant.settings or {}
    t_branding = tenant.branding or {}
    t_address = tenant.registered_address or ""

    # Clean fallback address from split fields if registered_address is not set in Tenant directly
    if not t_address and t_settings.get("company_address"):
        addr = t_settings["company_address"]
        t_address = ", ".join(filter(None, [
            addr.get("address_line1"),
            addr.get("address_line2"),
            addr.get("city"),
            addr.get("state"),
            addr.get("pin_code"),
            addr.get("country")
        ]))

    # Signatory details
    t_sig = t_settings.get("authorized_signatory", {})
    c_sig = company.authorized_signatory or {}
    sig_name = c_sig.get("name") or t_sig.get("name") or ""
    sig_desg = c_sig.get("designation") or t_sig.get("designation") or ""
    sig_url = c_sig.get("signature_url") or t_sig.get("signature_url") or ""

    # Bank details
    t_bank = t_settings.get("bank_details", {})
    c_bank = company.bank_details or {}
    bank_details = {
        "bank_name": c_bank.get("bank_name") or t_bank.get("bank_name") or "",
        "branch": c_bank.get("branch") or t_bank.get("branch_name") or "",
        "beneficiary_name": c_bank.get("beneficiary_name") or t_bank.get("account_holder_name") or company.name or tenant.name,
        "account_number": c_bank.get("account_number") or t_bank.get("account_number") or "",
        "ifsc_code": c_bank.get("ifsc_code") or t_bank.get("ifsc_code") or "",
        "upi_id": c_bank.get("upi_id") or t_bank.get("upi_id") or ""
    }

    # Contact details
    t_contact = t_settings.get("contact_information", {})
    c_contact = company.contact_details or {}
    contact_details = {
        "email": c_contact.get("email") or t_contact.get("email_address") or "",
        "phone": c_contact.get("phone") or t_contact.get("mobile_number") or t_contact.get("telephone_number") or "",
        "contact_person": t_contact.get("contact_person") or "",
        "website": t_contact.get("website") or ""
    }

    # Tax details
    gstin = company.gstin or tenant.gstin or t_settings.get("tax_information", {}).get("gst_number") or ""
    pan = t_settings.get("tax_information", {}).get("pan_number") or ""

    # Merge company into template rendering context
    context["company"] = {
        "name": company.name or tenant.name,
        "gst_status": company.gst_status,
        "gstin": gstin,
        "pan_number": pan,
        "address": company.address or t_address,
        "contact_details": contact_details,
        "bank_details": bank_details,
        "logo_url": company.logo_url or t_branding.get("logo_url") or "",
        "authorized_signatory": {
            "name": sig_name,
            "designation": sig_desg,
            "signature_url": sig_url
        },
        "seal_url": t_sig.get("seal_url") or ""
    }

    # 2. Try to fetch company custom template override
    template_record = await get_template_by_type(db, tenant_id, company_id, document_type)
    
    # 3. Resolve template source
    if template_record and template_record.template_html:
        template_html = template_record.template_html
    else:
        template_html = DEFAULT_HTML_TEMPLATES.get(document_type)

    if not template_html:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Template formatting for {document_type} could not be resolved."
        )

    # 4. Render HTML using Jinja2
    from jinja2 import Template
    tpl = Template(template_html)
    rendered_html = tpl.render(**context)

    # 5. Compile to PDF bytes using WeasyPrint
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=rendered_html).write_pdf()
    except (OSError, ImportError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF rendering is currently unavailable in this environment."
        ) from exc
    return pdf_bytes
