from typing import Optional
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: Optional[str] = None  # disambiguates when the email exists in multiple tenants
    otp_code: Optional[str] = None     # required when the account has 2FA enabled


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class SignUpRequest(BaseModel):
    company_name: str
    company_slug: str
    full_name: str
    email: EmailStr
    password: str
