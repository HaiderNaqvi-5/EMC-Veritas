from datetime import date
from uuid import UUID

from pydantic import BaseModel


class ActivityIssueResponse(BaseModel):
    activity_id: UUID
    issue_date: date
    issued_document_ids: list[UUID]
    skipped_student_ids: list[UUID]


class DocumentReissueResponse(BaseModel):
    superseded_document_id: UUID
    replacement_document_id: UUID
    issue_date: date
    version: int


class AdminDocumentResponse(BaseModel):
    id: UUID
    verification_id: str
    student_id: UUID
    student_name: str
    roll_number: str
    document_type: str
    context: str
    issue_date: date
    status: str
    version: int
    storage_key: str | None
    sha256: str | None
