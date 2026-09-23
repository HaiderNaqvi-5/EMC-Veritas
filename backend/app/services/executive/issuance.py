from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import (
    DocumentType,
    EmcSession,
    ExecutiveMembership,
    IssuedDocument,
    LeadershipTemplate,
    LeadershipTemplateField,
    MembershipStatus,
    Signatory,
    Society,
    Student,
)
from app.services.audit import record_audit_event
from app.services.documents.issuance import reserve_document
from app.services.executive.letters import (
    leadership_letter_values,
    missing_leadership_template_fields,
)
from app.services.executive.recognition import RECOGNITION_DOCUMENT_TYPES
from app.services.signatures.availability import missing_titles, select_effective_signatories
from app.services.signatures.policy import required_titles
from app.services.signatures.rendering import missing_signature_fields


class RecognitionPrerequisiteError(ValueError):
    """Raised when a closed session cannot safely reserve all leadership letters."""


@dataclass(frozen=True)
class _RecognitionPlan:
    membership: ExecutiveMembership
    document_type: DocumentType
    template: LeadershipTemplate
    values: dict[str, str | date]
    signatories: tuple[Signatory, ...]


def _active_signatories(db: Session) -> tuple[list[Signatory], dict[str, list[tuple[date, date | None]]]]:
    records = list(db.scalars(select(Signatory).where(Signatory.active.is_(True))).all())
    available: dict[str, list[tuple[date, date | None]]] = defaultdict(list)
    for signatory in records:
        available[signatory.official_title].append(
            (signatory.effective_start_date, signatory.effective_end_date)
        )
    return records, available


def _preflight_session_recognition(db: Session, session: EmcSession) -> list[_RecognitionPlan]:
    if session.end_date is None:
        raise RecognitionPrerequisiteError("A session end date is required for leadership recognition")
    rows = db.execute(
        select(ExecutiveMembership, Student, Society.name)
        .join(Student, ExecutiveMembership.student_id == Student.id)
        .outerjoin(Society, ExecutiveMembership.society_id == Society.id)
        .where(
            ExecutiveMembership.session_id == session.id,
            ExecutiveMembership.status == MembershipStatus.COMPLETED,
            Student.active.is_(True),
        )
        .order_by(ExecutiveMembership.role, ExecutiveMembership.id)
    ).all()
    signatories, availability = _active_signatories(db)
    plans: list[_RecognitionPlan] = []
    for membership, student, society_name in rows:
        role_end_date = membership.end_date or session.end_date
        for document_type in RECOGNITION_DOCUMENT_TYPES:
            existing = db.scalar(
                select(IssuedDocument.id).where(
                    IssuedDocument.executive_membership_id == membership.id,
                    IssuedDocument.document_type == document_type,
                )
            )
            if existing is not None:
                continue
            template = db.scalar(
                select(LeadershipTemplate).where(
                    LeadershipTemplate.role == membership.role,
                    LeadershipTemplate.document_type == document_type,
                    LeadershipTemplate.active.is_(True),
                    LeadershipTemplate.archived.is_(False),
                )
            )
            if template is None:
                raise RecognitionPrerequisiteError(
                    f"No active {document_type.value} template is configured for {membership.role}"
                )
            fields = list(
                db.scalars(
                    select(LeadershipTemplateField).where(
                        LeadershipTemplateField.leadership_template_id == template.id
                    )
                ).all()
            )
            missing_fields = missing_leadership_template_fields({field.field_name for field in fields})
            if missing_fields:
                raise RecognitionPrerequisiteError(
                    f"Leadership template for {membership.role} is missing fields: "
                    + ", ".join(sorted(missing_fields))
                )
            if template.signature_handling not in {"retain", "replace"}:
                raise RecognitionPrerequisiteError(
                    f"Leadership template for {membership.role} needs a retain-or-replace signature choice"
                )
            governing_date = role_end_date
            titles = required_titles(
                role=membership.role,
                appreciation=document_type is DocumentType.END_OF_TENURE_APPRECIATION,
            )
            missing_signatories = missing_titles(titles, availability, governing_date)
            if missing_signatories:
                raise RecognitionPrerequisiteError(
                    f"Required signatories are unavailable for {membership.role}: "
                    + ", ".join(missing_signatories)
                )
            selected = select_effective_signatories(signatories, titles, governing_date)
            if template.signature_handling == "replace":
                missing_boxes = missing_signature_fields(fields, selected)
                if missing_boxes:
                    raise RecognitionPrerequisiteError(
                        f"Leadership template for {membership.role} is missing signature fields: "
                        + ", ".join(missing_boxes)
                    )
            plans.append(
                _RecognitionPlan(
                    membership=membership,
                    document_type=document_type,
                    template=template,
                    values=dict(
                        leadership_letter_values(
                            student_name=student.full_name,
                            roll_number=student.roll_number,
                            role=membership.role,
                            society_name=society_name,
                            role_start_date=membership.start_date,
                            role_end_date=role_end_date,
                            session_name=session.name,
                            issue_date=session.end_date,
                        )
                    ),
                    signatories=tuple(selected.values()),
                )
            )
    return plans


def reserve_session_recognition(
    db: Session, *, session: EmcSession, actor_admin_id: UUID | None
) -> list[IssuedDocument]:
    """Reserve deterministic letters exactly once for completed memberships in a closed session."""
    plans = _preflight_session_recognition(db, session)
    documents = [
        reserve_document(
            db,
            student_id=plan.membership.student_id,
            executive_membership_id=plan.membership.id,
            leadership_template_id=plan.template.id,
            document_type=plan.document_type,
            issue_date=session.end_date,
            render_values=plan.values,
            actor_admin_id=actor_admin_id,
            signatories=plan.signatories,
        )
        for plan in plans
    ]
    record_audit_event(
        db,
        actor_admin_id=actor_admin_id,
        event_type="SESSION_LEADERSHIP_RECOGNITION_RESERVED",
        entity_type="session",
        entity_id=session.id,
        payload={"reserved_document_ids": [str(document.id) for document in documents]},
    )
    return documents
