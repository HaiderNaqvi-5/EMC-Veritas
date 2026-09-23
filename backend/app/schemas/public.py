from datetime import date
from uuid import UUID

from pydantic import BaseModel


class PublicDocument(BaseModel):
    id: UUID
    document_type: str
    title: str
    activity_date: date | None
    issue_date: date
    status: str


class StudentDocumentsResponse(BaseModel):
    full_name: str
    roll_number: str
    activity_certificates: list[PublicDocument]
    leadership_recognition: list[PublicDocument]


class VerificationResponse(BaseModel):
    verified: bool
    status: str
    verification_id: str
    full_name: str
    roll_number: str
    document_type: str
    context: str
    activity_date: date | None
    issue_date: date
