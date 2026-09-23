from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: UUID
    actor_admin_id: UUID | None
    event_type: str
    entity_type: str
    entity_id: str
    payload: dict
    created_at: datetime
