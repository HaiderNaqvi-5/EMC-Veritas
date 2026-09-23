from datetime import date
from uuid import UUID

from pydantic import BaseModel


class ActivityIssueResponse(BaseModel):
    activity_id: UUID
    issue_date: date
    issued_document_ids: list[UUID]
    skipped_student_ids: list[UUID]
