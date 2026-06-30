from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.company_template import CompanyTemplate
from app.models.company import Company
from app.repositories.base import TenantRepository
from app.services.crud_base import make_crud
from app.schemas.company_template import CompanyTemplateCreate, CompanyTemplateUpdate
from app.services.tenant import get_tenant

try:
    from weasyprint import HTML
except ImportError:
    HTML = None


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
    "QUOTATION_TEMPLATE1": """
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {
          font-family: Arial, sans-serif;
          margin: 0;
          padding: 10px;
          font-size: 11px;
          color: #000;
        }
        .text-center { text-align: center; }
        .text-right { text-align: right; }
        .text-bold { font-weight: bold; }
        
        .border-all { border: 1px solid #000; }
        .border-bottom { border-bottom: 1px solid #000; }
        .border-right { border-right: 1px solid #000; }
        
        table {
          width: 100%;
          border-collapse: collapse;
          margin: 0;
          padding: 0;
        }
        
        td, th {
          padding: 5px;
          vertical-align: top;
        }
        
        .header-table td {
          border: 1px solid #000;
          padding: 6px;
        }
        
        .items-table {
          border-left: 1px solid #000;
          border-right: 1px solid #000;
          border-bottom: 1px solid #000;
        }
        .items-table th {
          border: 1px solid #000;
          background-color: #f2f2f2;
          font-weight: bold;
          text-align: center;
        }
        .items-table td {
          border-right: 1px solid #000;
          padding: 4px 6px;
        }
        
        .hsn-table {
          border: 1px solid #000;
          margin-top: 10px;
          width: 100%;
        }
        .hsn-table th, .hsn-table td {
          border: 1px solid #000;
          text-align: center;
          padding: 4px;
        }
        
        .footer-table td {
          border: 1px solid #000;
          padding: 6px;
        }
        
        .title {
          font-size: 14px;
          font-weight: bold;
          letter-spacing: 1px;
          margin-bottom: 5px;
        }
      </style>
    </head>
    <body>
      <div style="border: 1px solid #000;">
        <!-- Title -->
        <div class="text-center border-bottom" style="padding: 5px; position: relative;">
          <span class="title">QUOTATION</span>
          <span style="position: absolute; right: 10px; top: 5px; font-weight: bold;">e-Invoice</span>
        </div>
        
        <!-- Header: Company & Quote Meta Details -->
        <table class="header-table" style="border: none;">
          <tr>
            <td style="width: 55%; border-left: none; border-top: none;">
              <div style="display: flex; align-items: flex-start; gap: 10px;">
                {% if company.logo_url %}
                  <img src="{{ company.logo_url }}" style="max-height: 45px; max-width: 150px; margin-right: 8px;" />
                {% endif %}
                <div>
                  <div class="text-bold" style="font-size: 13px;">{{ company.name }}</div>
                  <div>{{ company.address or '' }}</div>
                  {% if company.contact_details.phone %}<div>Ph No: {{ company.contact_details.phone }}</div>{% endif %}
                  {% if company.gstin %}<div>GSTIN/UIN: {{ company.gstin }}</div>{% endif %}
                  <div>State Name: Maharashtra, Code: 27</div>
                  {% if company.pan_number %}<div>Company PAN: {{ company.pan_number }}</div>{% endif %}
                </div>
              </div>
            </td>
            <td style="width: 45%; border-right: none; border-top: none; padding: 0;">
              <table style="height: 100%; border: none;">
                <tr class="border-bottom">
                  <td class="border-right" style="width: 50%;">
                    <span style="color: #555;">Quotation No.</span><br/>
                    <span class="text-bold">{{ doc.quotation_number }}</span>
                  </td>
                  <td>
                    <span style="color: #555;">Dated</span><br/>
                    <span class="text-bold">{{ doc.created_at.strftime('%d-%b-%y') if doc.created_at else '' }}</span>
                  </td>
                </tr>
                <tr class="border-bottom">
                  <td class="border-right">
                    <span style="color: #555;">Valid Until</span><br/>
                    <span class="text-bold">{{ doc.valid_until.strftime('%d-%b-%y') if doc.valid_until else '—' }}</span>
                  </td>
                  <td>
                    <span style="color: #555;">Terms of Payment</span><br/>
                    <span class="text-bold">Advance</span>
                  </td>
                </tr>
                <tr>
                  <td colspan="2">
                    <span style="color: #555;">Terms of Delivery</span><br/>
                    <span>Immediate / As per schedule</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          
          <!-- Addresses -->
          <tr>
            <td style="border-left: none; border-bottom: none;">
              <span style="color: #555;">Consignee (Ship to)</span><br/>
              <div class="text-bold">{{ customer.name }}</div>
              <div>{{ customer.shipping_address or customer.address or '' }}</div>
              {% if customer.phone %}<div>Mob: {{ customer.phone }}</div>{% endif %}
              {% if customer.gstin %}<div>GSTIN/UIN: {{ customer.gstin }}</div>{% endif %}
            </td>
            <td style="border-right: none; border-bottom: none;">
              <span style="color: #555;">Buyer (Bill to)</span><br/>
              <div class="text-bold">{{ customer.name }}</div>
              <div>{{ customer.billing_address or customer.address or '' }}</div>
              {% if customer.phone %}<div>Mob: {{ customer.phone }}</div>{% endif %}
              {% if customer.gstin %}<div>GSTIN/UIN: {{ customer.gstin }}</div>{% endif %}
            </td>
          </tr>
        </table>
        
        <!-- Items Table -->
        <table class="items-table">
          <thead>
            <tr>
              <th style="width: 5%;">Sl No.</th>
              <th style="width: 50%;">Description of Goods</th>
              <th style="width: 12%;">HSN/SAC</th>
              <th style="width: 8%;">Quantity</th>
              <th style="width: 10%;">Rate</th>
              <th style="width: 5%;">per</th>
              <th style="width: 10%;">Amount</th>
            </tr>
          </thead>
          <tbody>
            {% for item in items %}
            <tr style="min-height: 25px;">
              <td class="text-center">{{ loop.index }}</td>
              <td>
                <div class="text-bold">{{ item.get('description', '') }}</div>
                {% if item.get('details') %}
                  <div style="color: #555; font-size: 9px;">{{ item.get('details') }}</div>
                {% endif %}
              </td>
              <td class="text-center">{{ item.get('hsn_code') or '84713010' }}</td>
              <td class="text-center">{{ item.get('quantity', 0) }} Pcs</td>
              <td class="text-right">{{ item.get('unit_price', 0) | float | round(2) }}</td>
              <td class="text-center">Pcs</td>
              <td class="text-right text-bold">{{ item.get('amount', 0) | float | round(2) }}</td>
            </tr>
            {% endfor %}
            
            {% if items|length < 5 %}
              {% for i in range(5 - items|length) %}
              <tr style="height: 20px;">
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
              </tr>
              {% endfor %}
            {% endif %}
            
            {% if doc.cgst_amount or doc.sgst_amount or doc.igst_amount %}
              {% if doc.cgst_amount %}
              <tr>
                <td>&nbsp;</td>
                <td class="text-right text-bold">Output CGST</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td class="text-right text-bold">{{ doc.cgst_amount | float | round(2) }}</td>
              </tr>
              {% endif %}
              {% if doc.sgst_amount %}
              <tr>
                <td>&nbsp;</td>
                <td class="text-right text-bold">Output SGST</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td class="text-right text-bold">{{ doc.sgst_amount | float | round(2) }}</td>
              </tr>
              {% endif %}
              {% if doc.igst_amount %}
              <tr>
                <td>&nbsp;</td>
                <td class="text-right text-bold">Output IGST</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td class="text-right text-bold">{{ doc.igst_amount | float | round(2) }}</td>
              </tr>
              {% endif %}
            {% endif %}
            
            <tr style="border-top: 1px solid #000; background-color: #f9f9f9; font-weight: bold;">
              <td colspan="3" class="text-right">Total</td>
              <td class="text-center">
                {% set total_qty = 0 %}
                {% for item in items %}
                  {% set total_qty = total_qty + (item.get('quantity', 0) | int) %}
                {% endfor %}
                {{ total_qty }} Pcs
              </td>
              <td colspan="2">&nbsp;</td>
              <td class="text-right">₹ {{ doc.total_amount | float | round(2) }}</td>
            </tr>
          </tbody>
        </table>
        
        <div class="border-bottom" style="padding: 6px;">
          <div>Amount Chargeable (in words)</div>
          <div class="text-bold" style="font-size: 11px;">INR {{ doc.total_amount | float | round(2) }} (Approx.)</div>
        </div>
        
        {% if doc.cgst_amount or doc.sgst_amount or doc.igst_amount %}
        <div style="padding: 6px;" class="border-bottom">
          <table class="hsn-table">
            <thead>
              <tr>
                <th rowspan="2">HSN/SAC</th>
                <th rowspan="2">Taxable Value</th>
                <th colspan="2">Central Tax</th>
                <th colspan="2">State Tax</th>
                <th rowspan="2">Total Tax Amount</th>
              </tr>
              <tr>
                <th>Rate</th>
                <th>Amount</th>
                <th>Rate</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>84713010</td>
                <td>{{ doc.subtotal | float | round(2) }}</td>
                <td>9%</td>
                <td>{{ doc.cgst_amount | float | round(2) if doc.cgst_amount else '0.00' }}</td>
                <td>9%</td>
                <td>{{ doc.sgst_amount | float | round(2) if doc.sgst_amount else '0.00' }}</td>
                <td>{{ (doc.cgst_amount | float + doc.sgst_amount | float) | round(2) if (doc.cgst_amount and doc.sgst_amount) else '0.00' }}</td>
              </tr>
              <tr style="font-weight: bold;">
                <td>Total</td>
                <td>{{ doc.subtotal | float | round(2) }}</td>
                <td>&nbsp;</td>
                <td>{{ doc.cgst_amount | float | round(2) if doc.cgst_amount else '0.00' }}</td>
                <td>&nbsp;</td>
                <td>{{ doc.sgst_amount | float | round(2) if doc.sgst_amount else '0.00' }}</td>
                <td>{{ (doc.cgst_amount | float + doc.sgst_amount | float) | round(2) if (doc.cgst_amount and doc.sgst_amount) else '0.00' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        {% endif %}
        
        <table class="footer-table" style="border: none;">
          <tr>
            <td style="width: 50%; border-left: none; border-bottom: none;">
              <div class="text-bold">Company's Bank Details</div>
              <div>Bank Name: {{ company.bank_details.bank_name or 'HDFC Bank' }}</div>
              <div>A/c Holder's Name: {{ company.bank_details.beneficiary_name or company.name }}</div>
              <div>A/c No: {{ company.bank_details.account_number or '05922560003360' }}</div>
              <div>Branch & IFS Code: {{ company.bank_details.branch or 'Mumbai' }} &amp; {{ company.bank_details.ifsc_code or 'HDFC0000592' }}</div>
              
              {% if doc.terms %}
                <div style="margin-top: 10px; font-size: 8px; color: #555;">
                  <span class="text-bold">Terms &amp; Conditions:</span><br/>
                  {{ doc.terms | safe }}
                </div>
              {% endif %}
            </td>
            <td style="width: 50%; border-right: none; border-bottom: none; text-align: right; position: relative;">
              <div>For <span class="text-bold">{{ company.name }}</span></div>
              
              <div style="margin-top: 15px; display: inline-block; position: relative; height: 50px;">
                {% if company.authorized_signatory.signature_url %}
                  <img src="{{ company.authorized_signatory.signature_url }}" style="max-height: 35px; z-index: 2; position: relative;" />
                {% endif %}
                {% if company.seal_url %}
                  <img src="{{ company.seal_url }}" style="max-height: 45px; position: absolute; right: 10px; top: -5px; opacity: 0.85; z-index: 1;" />
                {% endif %}
              </div>
              
              <div style="margin-top: 5px;">Authorized Signatory</div>
              {% if company.authorized_signatory.name %}
                <div style="font-size: 9px; color: #555;">({{ company.authorized_signatory.name }})</div>
              {% endif %}
            </td>
          </tr>
        </table>
      </div>
      <div class="text-center" style="margin-top: 10px; font-size: 9px; color: #555;">
        SUBJECT TO MUMBAI JURISDICTION<br/>
        This is a Computer Generated Invoice
      </div>
    </body>
    </html>
    """,
    "QUOTATION_TEMPLATE2": """
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {
          font-family: sans-serif;
          padding: 30px;
          font-size: 12px;
          color: #333;
          background-color: #f7f9fb;
        }
        .receipt-card {
          border: 1px solid #d3dbde;
          background-color: #ffffff;
          border-radius: 8px;
          padding: 30px;
          max-width: 600px;
          margin: 0 auto;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }
        .logo {
          max-height: 50px;
          margin-bottom: 10px;
        }
        .header {
          text-align: center;
          border-bottom: 2px solid #003366;
          padding-bottom: 15px;
          margin-bottom: 20px;
        }
        .title {
          font-size: 20px;
          font-weight: bold;
          color: #003366;
          letter-spacing: 1px;
        }
        .subtitle {
          font-size: 12px;
          color: #666;
          margin-top: 5px;
          font-weight: bold;
        }
        .details-table {
          width: 100%;
          border-collapse: collapse;
          margin-bottom: 20px;
        }
        .details-table tr {
          border-bottom: 1px solid #f0f0f0;
        }
        .details-table td {
          padding: 10px 8px;
          vertical-align: middle;
        }
        .details-table td:first-child {
          font-weight: bold;
          color: #555;
          width: 40%;
        }
        .details-table td:last-child {
          text-align: left;
          color: #000;
        }
        .footer {
          text-align: center;
          font-size: 10px;
          color: #888;
          margin-top: 25px;
          border-top: 1px solid #eee;
          padding-top: 15px;
        }
        .status-badge {
          background-color: #e3f2fd;
          color: #0d47a1;
          padding: 3px 8px;
          border-radius: 4px;
          font-weight: bold;
          font-size: 10px;
          display: inline-block;
          text-transform: uppercase;
        }
      </style>
    </head>
    <body>
      <div class="receipt-card">
        <div class="header">
          {% if company.logo_url %}
            <img class="logo" src="{{ company.logo_url }}" /><br/>
          {% endif %}
          <div class="title">e-Quotation</div>
          <div class="subtitle">Other Bank Transaction Details</div>
        </div>

        <table class="details-table">
          <tr>
            <td>Txn Date</td>
            <td>{{ doc.created_at.strftime('%d/%m/%Y') if doc.created_at else '' }}</td>
          </tr>
          <tr>
            <td>Quotation Number</td>
            <td style="font-weight: bold; color: #003366;">{{ doc.quotation_number }}</td>
          </tr>
          <tr>
            <td>Name (Customer)</td>
            <td style="text-transform: uppercase; font-weight: bold;">{{ customer.name }}</td>
          </tr>
          {% if customer.phone %}
          <tr>
            <td>Customer Phone</td>
            <td>{{ customer.phone }}</td>
          </tr>
          {% endif %}
          {% if customer.gstin %}
          <tr>
            <td>Ifsc Code (GSTIN)</td>
            <td>{{ customer.gstin }}</td>
          </tr>
          {% endif %}
          <tr>
            <td>From Company</td>
            <td>{{ company.name }}</td>
          </tr>
          <tr>
            <td>Sender Information (Bank details)</td>
            <td>{{ company.bank_details.bank_name or 'Indian Overseas Bank' }} - A/C {{ company.bank_details.account_number or '264302000040133' }}</td>
          </tr>
          <tr>
            <td>Amount</td>
            <td style="font-size: 15px; font-weight: bold; color: #003366;">₹ {{ doc.total_amount }}</td>
          </tr>
          <tr>
            <td>UTR Number (Quote Status)</td>
            <td><span class="status-badge">{{ doc.status }}</span></td>
          </tr>
          <tr>
            <td>Status</td>
            <td style="font-weight: bold; color: #2e7d32;">Amount Sent to Other Bank (Approved)</td>
          </tr>
        </table>

        <div class="footer">
          This is a computer generated electronic receipt. For any questions, please contact {{ company.contact_details.email or 'support@durwankur.com' }}.
        </div>
      </div>
    </body>
    </html>
    """,
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
        if HTML is None:
            from weasyprint import HTML as RealHTML
            pdf_bytes = RealHTML(string=rendered_html).write_pdf()
        else:
            pdf_bytes = HTML(string=rendered_html).write_pdf()
    except (OSError, ImportError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF rendering is currently unavailable in this environment."
        ) from exc
    return pdf_bytes
