from uuid import UUID
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.cash_collection import CashCollection, CashCollectionStatus
from app.models.cash_collection_log import CashCollectionLog
from app.repositories.base import TenantRepository
from app.services.crud_base import make_crud
from app.schemas.cash_collection import CashCollectionCreate, CashCollectionAction

class CashCollectionRepository(TenantRepository[CashCollection]):
    model = CashCollection

class CashCollectionLogRepository(TenantRepository[CashCollectionLog]):
    model = CashCollectionLog

list_cash_collections, get_cash_collection, _create_cash_raw, _update_cash_raw = make_crud(CashCollectionRepository, CashCollection)

async def create_cash_collection(db: AsyncSession, tenant_id: UUID, employee_id: UUID, payload: CashCollectionCreate) -> CashCollection:
    repo = CashCollectionRepository(db, tenant_id)
    # Check if optional ticket or invoice exists
    if payload.service_ticket_id:
        from app.services.service_ticket import ServiceTicketRepository
        ticket = await ServiceTicketRepository(db, tenant_id).get(payload.service_ticket_id)
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service Ticket not found")
    if payload.invoice_id:
        from app.services.invoice import InvoiceRepository
        inv = await InvoiceRepository(db, tenant_id).get(payload.invoice_id)
        if not inv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    obj = CashCollection(
        employee_id=employee_id,
        customer_name=payload.customer_name,
        company_id=payload.company_id,
        service_ticket_id=payload.service_ticket_id,
        invoice_id=payload.invoice_id,
        amount=payload.amount,
        collected_at=payload.collected_at,
        remarks=payload.remarks,
        receipt_photo_url=payload.receipt_photo_url,
        status=CashCollectionStatus.PENDING,
    )
    return await repo.create(obj)

async def review_cash_collection(db: AsyncSession, tenant_id: UUID, cash_collection_id: UUID, action_by: UUID, payload: CashCollectionAction) -> CashCollection:
    repo = CashCollectionRepository(db, tenant_id)
    log_repo = CashCollectionLogRepository(db, tenant_id)
    
    collection = await repo.get(cash_collection_id)
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cash Collection record not found")
        
    if collection.status != CashCollectionStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending collections can be verified")

    action = payload.action.upper()
    if action == "APPROVED":
        collection.status = CashCollectionStatus.RECEIVED
    elif action == "REJECTED":
        collection.status = CashCollectionStatus.REJECTED
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action. Must be APPROVED or REJECTED")

    # Save collection
    await repo.save(collection)

    # Add log entry
    log = CashCollectionLog(
        cash_collection_id=cash_collection_id,
        action=action,
        action_by=action_by,
        notes=payload.notes
    )
    await log_repo.create(log)
    
    # Sync in-memory relationship for response serialization
    collection.logs.append(log)
    
    return collection
