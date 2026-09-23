import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.domain import AuditLog


def record_audit_event(db: Session, *, event_type: str, entity_type: str, entity_id: UUID | str, payload: dict, actor_admin_id: UUID | None = None) -> AuditLog:
    event = AuditLog(actor_admin_id=actor_admin_id, event_type=event_type, entity_type=entity_type, entity_id=str(entity_id), payload_json=json.dumps(payload, sort_keys=True))
    db.add(event)
    return event
