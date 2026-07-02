from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, SignUpRequest
from app.services import auth as auth_service

router = APIRouter()


class Verify2FARequest(BaseModel):
    code: str


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.login(db, payload)


@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(payload: SignUpRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.signup(db, payload)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.refresh(db, payload)


@router.get("/me")
async def me(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Identity of the authenticated user — drives UI route guards (role,
    platform-admin) and profile display."""
    return await auth_service.current_user_info(db, current_user.user_id)


@router.post("/2fa/enroll")
async def enroll_2fa(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Begin TOTP enrollment — returns a secret + otpauth:// provisioning URI."""
    return await auth_service.enroll_2fa(db, current_user.user_id)


@router.post("/2fa/verify")
async def verify_2fa(
    payload: Verify2FARequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Verify the first TOTP code and enable 2FA."""
    return await auth_service.verify_2fa(db, current_user.user_id, payload.code)
