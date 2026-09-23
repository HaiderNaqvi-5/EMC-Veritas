from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.domain import DocumentStatus, DocumentType, IssuedDocument
from app.services.verification.identifiers import new_verification_id


def reserve_document(
    db: Session, *, student_id: UUID, document_type: DocumentType, issue_date: date, activity_id: UUID | None = None
) -> IssuedDocument:
    document = IssuedDocument(
        student_id=student_id,
        activity_id=activity_id,
        document_type=document_type,
        issue_date=issue_date,
        verification_id=new_verification_id(),
        status=DocumentStatus.VALID,
    )
    db.add(document)
    return document
