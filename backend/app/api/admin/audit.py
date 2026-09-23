import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.admin.dependencies import super_admin_required
from app.db.session import get_db
from app.models.domain import Admin, AuditLog
from app.schemas.audit import AuditEventResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditEventResponse])
def list_audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> list[AuditEventResponse]:
    events = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return [
        AuditEventResponse(
            id=event.id,
            actor_admin_id=event.actor_admin_id,
            event_type=event.event_type,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            payload=json.loads(event.payload_json),
            created_at=event.created_at,
        )
        for event in events
    ]
