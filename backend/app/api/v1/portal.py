"""Customer self-service portal API (SRS 4.2).

All routes (except login/refresh) require a portal-scoped token and are scoped to
the authenticated customer via ``get_current_portal_user``.
"""
from uuid import UUID
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_portal_user, PortalUser
from app.services import portal as portal_service

router = APIRouter()


class PortalLoginRequest(BaseModel):
    email: str
    password: str
    tenant_slug: str


class PortalRefreshRequest(BaseModel):
    refresh_token: str


class TicketCreateRequest(BaseModel):
    complaint: str
    priority: str = "medium"
    site_id: Optional[UUID] = None


class CommentRequest(BaseModel):
    body: str


@router.post("/login")
async def login(payload: PortalLoginRequest, db: AsyncSession = Depends(get_db)):
    return await portal_service.login(db, payload.email, payload.password, payload.tenant_slug)


@router.post("/refresh")
async def refresh(payload: PortalRefreshRequest, db: AsyncSession = Depends(get_db)):
    return await portal_service.refresh(db, payload.refresh_token)


@router.get("/me")
async def me(db: AsyncSession = Depends(get_db), portal: PortalUser = Depends(get_current_portal_user)):
    return await portal_service.me(db, portal)


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db), portal: PortalUser = Depends(get_current_portal_user)):
    return await portal_service.dashboard(db, portal)


@router.get("/sites")
async def sites(db: AsyncSession = Depends(get_db), portal: PortalUser = Depends(get_current_portal_user)):
    return await portal_service.list_sites(db, portal)


@router.get("/assets")
async def assets(db: AsyncSession = Depends(get_db), portal: PortalUser = Depends(get_current_portal_user)):
    return await portal_service.list_assets(db, portal)


@router.get("/amc")
async def amc(db: AsyncSession = Depends(get_db), portal: PortalUser = Depends(get_current_portal_user)):
    return await portal_service.list_amc(db, portal)


@router.get("/invoices")
async def invoices(db: AsyncSession = Depends(get_db), portal: PortalUser = Depends(get_current_portal_user)):
    return await portal_service.list_invoices(db, portal)


@router.get("/tickets")
async def tickets(db: AsyncSession = Depends(get_db), portal: PortalUser = Depends(get_current_portal_user)):
    return await portal_service.list_tickets(db, portal)


@router.post("/tickets", status_code=201)
async def create_ticket(payload: TicketCreateRequest, db: AsyncSession = Depends(get_db),
                        portal: PortalUser = Depends(get_current_portal_user)):
    return await portal_service.create_ticket(
        db, portal, priority=payload.priority, complaint=payload.complaint, site_id=payload.site_id)


@router.get("/tickets/{ticket_id}")
async def ticket_detail(ticket_id: UUID, db: AsyncSession = Depends(get_db),
                        portal: PortalUser = Depends(get_current_portal_user)):
    return await portal_service.get_ticket(db, portal, ticket_id)


@router.post("/tickets/{ticket_id}/comments", status_code=201)
async def add_comment(ticket_id: UUID, payload: CommentRequest, db: AsyncSession = Depends(get_db),
                      portal: PortalUser = Depends(get_current_portal_user)):
    return await portal_service.add_comment(db, portal, ticket_id, payload.body)
