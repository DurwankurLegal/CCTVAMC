from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser, require_permission
from app.schemas.installation import (
    InstallationCreate, InstallationUpdate, InstallationResponse,
    SurveyUpdate, HandoverRequest,
)
from app.services import installation as inst_service

router = APIRouter()


@router.get("", response_model=List[InstallationResponse])
async def list_installations(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await inst_service.list_installations(db, current_user.tenant_id, offset, limit)


@router.post("", response_model=InstallationResponse, status_code=201)
async def create_installation(
    payload: InstallationCreate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installations:write")),
):
    return await inst_service.create_installation(db, current_user.tenant_id, payload)


@router.get("/{inst_id}", response_model=InstallationResponse)
async def get_installation(
    inst_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await inst_service.get_installation(db, current_user.tenant_id, inst_id)


@router.patch("/{inst_id}", response_model=InstallationResponse)
async def update_installation(
    inst_id: UUID, payload: InstallationUpdate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installations:write")),
):
    return await inst_service.update_installation(db, current_user.tenant_id, inst_id, payload)


@router.post("/{inst_id}/survey", response_model=InstallationResponse)
async def record_survey(
    inst_id: UUID, payload: SurveyUpdate, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installations:write")),
):
    return await inst_service.record_survey(db, current_user.tenant_id, inst_id, payload)


@router.post("/{inst_id}/handover-otp")
async def request_handover_otp(
    inst_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installations:write")),
):
    otp = await inst_service.request_handover_otp(db, current_user.tenant_id, inst_id)
    return {"otp": otp}


@router.post("/{inst_id}/handover", response_model=InstallationResponse)
async def handover(
    inst_id: UUID, payload: HandoverRequest, db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installations:write")),
):
    return await inst_service.handover(db, current_user.tenant_id, inst_id, payload)
