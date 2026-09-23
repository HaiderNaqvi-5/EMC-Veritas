from datetime import date
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.domain import DocumentStatus, DocumentType, IssuedDocument
from app.services.audit import record_audit_event
from app.services.verification.identifiers import new_verification_id


def reserve_document(
    db: Session,
    *,
    student_id: UUID,
    document_type: DocumentType,
    issue_date: date,
    activity_id: UUID | None = None,
    actor_admin_id: UUID | None = None,
    version: int = 1,
) -> IssuedDocument:
    document = IssuedDocument(
        id=uuid4(),
        student_id=student_id,
        activity_id=activity_id,
        document_type=document_type,
        issue_date=issue_date,
        verification_id=new_verification_id(),
        status=DocumentStatus.VALID,
        version=version,
    )
    db.add(document)
    record_audit_event(
        db,
        actor_admin_id=actor_admin_id,
        event_type="DOCUMENT_RESERVED",
        entity_type="issued_document",
        entity_id=document.id,
        payload={
            "document_type": document_type.value,
            "issue_date": issue_date.isoformat(),
            "version": version,
        },
    )
    return document


def revoke_document(document: IssuedDocument) -> None:
    document.status = DocumentStatus.REVOKED


def supersede_document(document: IssuedDocument) -> None:
    document.status = DocumentStatus.SUPERSEDED
