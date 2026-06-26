from uuid import UUID
from typing import Optional
from pydantic import BaseModel

class CompanyTemplateBase(BaseModel):
    company_id: UUID
    document_type: str
    template_html: str
    header_html: Optional[str] = None
    footer_html: Optional[str] = None
    is_active: bool = True

class CompanyTemplateCreate(CompanyTemplateBase):
    pass

class CompanyTemplateUpdate(BaseModel):
    template_html: Optional[str] = None
    header_html: Optional[str] = None
    footer_html: Optional[str] = None
    is_active: Optional[bool] = None

class CompanyTemplateResponse(CompanyTemplateBase):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
