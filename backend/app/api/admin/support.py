from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.admin.dependencies import current_active_admin
from app.db.session import get_db
from app.models.domain import Admin, SupportRequest, SupportRequestStatus
from app.schemas.support import SupportRequestResponse, SupportRequestUpdate
from app.services.audit import record_audit_event

router = APIRouter(prefix="/support-requests", tags=["admin-support"])


@router.get("", response_model=list[SupportRequestResponse])
def list_support_requests(
    request_status: SupportRequestStatus | None = Query(default=None, alias="status"),
    query: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
    _: Admin = Depends(current_active_admin),
) -> list[SupportRequest]:
    statement = select(SupportRequest)
    if request_status is not None:
        statement = statement.where(SupportRequest.status == request_status)
    if query and (term := query.strip()):
        search = f"%{term}%"
        statement = statement.where(
            or_(
                SupportRequest.ticket_number.ilike(search),
                SupportRequest.roll_number.ilike(search),
                SupportRequest.full_name.ilike(search),
                SupportRequest.contact_email.ilike(search),
            )
        )
    return list(db.scalars(statement.order_by(SupportRequest.created_at.desc())).all())


@router.patch("/{request_id}", response_model=SupportRequestResponse)
def update_support_request(
    request_id: UUID,
    payload: SupportRequestUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(current_active_admin),
) -> SupportRequest:
    item = db.get(SupportRequest, request_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support request not found")

    previous_status = item.status
    item.status = payload.status
    item.admin_notes = payload.admin_notes
    item.resolution_message = payload.resolution_message
    if payload.status == SupportRequestStatus.RESOLVED:
        item.resolved_by_admin_id = admin.id
        item.resolved_at = datetime.now(UTC)
    else:
        item.resolved_by_admin_id = None
        item.resolved_at = None

    record_audit_event(
        db,
        event_type="SUPPORT_REQUEST_UPDATED",
        entity_type="support_request",
        entity_id=item.id,
        actor_admin_id=admin.id,
        payload={
            "ticket_number": item.ticket_number,
            "previous_status": previous_status.value,
            "status": item.status.value,
        },
    )
    db.commit()
    db.refresh(item)
    return item
