from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class SignatoryResponse(BaseModel):
    id: UUID
    name: str
    official_title: str
    effective_start_date: date
    effective_end_date: date | None
    active: bool
    created_at: datetime
