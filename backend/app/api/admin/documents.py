import json
from collections import defaultdict
from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.admin.dependencies import current_active_admin
from app.db.session import get_db
from app.models.domain import (
    Activity,
    ActivityParticipant,
    ActivityStatus,
    Admin,
    DocumentSignatory,
    DocumentStatus,
    DocumentType,
    IssuedDocument,
    LeadershipTemplate,
    Signatory,
    Student,
    Template,
    TemplateField,
)
from app.schemas.documents import (
    ActivityIssueResponse,
    AdminDocumentResponse,
    DocumentReissueResponse,
)
from app.services.audit import record_audit_event
from app.services.documents.issuance import reserve_document
from app.services.signatures.availability import missing_titles, select_effective_signatories
from app.services.signatures.policy import required_titles
from app.services.signatures.rendering import missing_signature_fields
from app.services.templates.fields import missing_required_fields

router = APIRouter(prefix="/documents", tags=["documents"])
EMC_TIMEZONE = ZoneInfo("Asia/Karachi")


def _admin_document_response(
    document: IssuedDocument, student: Student, activity_name: str | None, template_name: str | None
) -> AdminDocumentResponse:
    return AdminDocumentResponse(
        id=document.id,
        verification_id=document.verification_id,
        student_id=student.id,
        student_name=student.full_name,
        roll_number=student.roll_number,
        document_type=document.document_type.value,
        context=activity_name or template_name or document.document_type.value.replace("_", " ").title(),
        issue_date=document.issue_date,
        status=document.status.value,
        version=document.version,
        storage_key=document.storage_key,
        sha256=document.sha256,
    )


@router.get("", response_model=list[AdminDocumentResponse])
def list_issued_documents(
    student_id: UUID | None = None,
    status_filter: DocumentStatus | None = None,
    document_type: DocumentType | None = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(current_active_admin),
) -> list[AdminDocumentResponse]:
    query = (
        select(IssuedDocument, Student, Activity.name, LeadershipTemplate.name)
        .join(Student, IssuedDocument.student_id == Student.id)
        .outerjoin(Activity, IssuedDocument.activity_id == Activity.id)
        .outerjoin(LeadershipTemplate, IssuedDocument.leadership_template_id == LeadershipTemplate.id)
        .order_by(IssuedDocument.created_at.desc())
    )
    if student_id is not None:
        query = query.where(IssuedDocument.student_id == student_id)
    if status_filter is not None:
        query = query.where(IssuedDocument.status == status_filter)
    if document_type is not None:
        query = query.where(IssuedDocument.document_type == document_type)
    return [_admin_document_response(*row) for row in db.execute(query).all()]


@router.get("/{document_id}", response_model=AdminDocumentResponse)
def get_issued_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(current_active_admin),
) -> AdminDocumentResponse:
    row = db.execute(
        select(IssuedDocument, Student, Activity.name, LeadershipTemplate.name)
        .join(Student, IssuedDocument.student_id == Student.id)
        .outerjoin(Activity, IssuedDocument.activity_id == Activity.id)
        .outerjoin(LeadershipTemplate, IssuedDocument.leadership_template_id == LeadershipTemplate.id)
        .where(IssuedDocument.id == document_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Issued document not found")
    return _admin_document_response(*row)


@router.post("/activities/{activity_id}/issue", response_model=ActivityIssueResponse)
def issue_activity_documents(
    activity_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(current_active_admin),
) -> ActivityIssueResponse:
    activity = db.get(Activity, activity_id)
    if activity is None or activity.status == ActivityStatus.ARCHIVED:
        raise HTTPException(status_code=404, detail="Activity not found")
    if activity.status != ActivityStatus.READY:
        raise HTTPException(status_code=409, detail="Only READY activities can be issued and published")
    if activity.template_id is None:
        raise HTTPException(status_code=409, detail="An approved certificate template is required before issue")
    template = db.scalar(
        select(Template).where(
            Template.id == activity.template_id,
            Template.approved.is_(True),
            Template.archived.is_(False),
        )
    )
    if template is None:
        raise HTTPException(status_code=409, detail="An approved certificate template is required before issue")
    if template.signature_handling is None:
        raise HTTPException(
            status_code=409,
            detail="The template requires an explicit retain or replace signature choice before issue",
        )
    template_fields = db.scalars(
        select(TemplateField).where(TemplateField.template_id == template.id)
    ).all()
    field_names = {field.field_name for field in template_fields}
    missing_fields = missing_required_fields(field_names)
    if missing_fields:
        raise HTTPException(
            status_code=409,
            detail="Template is missing required fields: " + ", ".join(sorted(missing_fields)),
        )

    active_signatories = list(
        db.scalars(select(Signatory).where(Signatory.active.is_(True))).all()
    )
    available_signatories: dict[str, list[tuple[date, date | None]]] = defaultdict(list)
    for signatory in active_signatories:
        available_signatories[signatory.official_title].append(
            (signatory.effective_start_date, signatory.effective_end_date)
        )
    required_signatory_titles = required_titles()
    missing_signatories = missing_titles(required_signatory_titles, available_signatories, activity.activity_date)
    if missing_signatories:
        raise HTTPException(
            status_code=409,
            detail="Required signatories are unavailable: " + ", ".join(missing_signatories),
        )
    selected_signatories = select_effective_signatories(
        active_signatories, required_signatory_titles, activity.activity_date
    )
    if template.signature_handling == "replace":
        missing_signature_boxes = missing_signature_fields(template_fields, selected_signatories)
        if missing_signature_boxes:
            raise HTTPException(
                status_code=409,
                detail="Template is missing signature fields: " + ", ".join(missing_signature_boxes),
            )

    issue_date = activity.issue_date or datetime.now(EMC_TIMEZONE).date()
    eligible_student_ids = list(
        db.scalars(
            select(ActivityParticipant.student_id)
            .join(Student, ActivityParticipant.student_id == Student.id)
            .where(
                ActivityParticipant.activity_id == activity.id,
                ActivityParticipant.eligible.is_(True),
                Student.active.is_(True),
            )
        ).all()
    )
    if not eligible_student_ids:
        raise HTTPException(status_code=409, detail="No eligible participants are available for issue")

    existing_student_ids = set(
        db.scalars(
            select(IssuedDocument.student_id).where(
                IssuedDocument.activity_id == activity.id,
                IssuedDocument.document_type == DocumentType.ACTIVITY_CERTIFICATE,
                IssuedDocument.status == DocumentStatus.VALID,
            )
        ).all()
    )
    issued_document_ids: list[UUID] = []
    skipped_student_ids: list[UUID] = []
    for student_id in eligible_student_ids:
        if student_id in existing_student_ids:
            skipped_student_ids.append(student_id)
            continue
        document = reserve_document(
            db,
            student_id=student_id,
            activity_id=activity.id,
            template_id=template.id,
            document_type=DocumentType.ACTIVITY_CERTIFICATE,
            issue_date=issue_date,
            render_values={
                "student_name": db.get(Student, student_id).full_name,
                "roll_number": db.get(Student, student_id).roll_number,
                "activity_name": activity.name,
                "activity_date": activity.activity_date,
                "issue_date": issue_date,
            },
            actor_admin_id=admin.id,
            signatories=tuple(selected_signatories.values()),
        )
        issued_document_ids.append(document.id)
    activity.issue_date = issue_date
    activity.status = ActivityStatus.PUBLISHED
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="ACTIVITY_DOCUMENTS_ISSUED",
        entity_type="activity",
        entity_id=activity.id,
        payload={
            "issue_date": issue_date.isoformat(),
            "issued_count": len(issued_document_ids),
            "skipped_count": len(skipped_student_ids),
        },
    )
    db.commit()
    return ActivityIssueResponse(
        activity_id=activity.id,
        issue_date=issue_date,
        issued_document_ids=issued_document_ids,
        skipped_student_ids=skipped_student_ids,
    )


@router.post("/{document_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_issued_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(current_active_admin),
) -> None:
    document = db.get(IssuedDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Issued document not found")
    if document.status != DocumentStatus.VALID:
        raise HTTPException(status_code=409, detail="Only valid documents can be revoked")
    document.status = DocumentStatus.REVOKED
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="DOCUMENT_REVOKED",
        entity_type="issued_document",
        entity_id=document.id,
        payload={"verification_id": document.verification_id, "version": document.version},
    )
    db.commit()


@router.post("/{document_id}/reissue", response_model=DocumentReissueResponse)
def reissue_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(current_active_admin),
) -> DocumentReissueResponse:
    document = db.get(IssuedDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Issued document not found")
    if document.status != DocumentStatus.VALID:
        raise HTTPException(status_code=409, detail="Only valid documents can be reissued")
    if document.document_type in {
        DocumentType.LEADERSHIP_RECOGNITION,
        DocumentType.END_OF_TENURE_APPRECIATION,
    }:
        return _reissue_leadership_document(db, document, admin)
    if document.activity_id is None or document.document_type != DocumentType.ACTIVITY_CERTIFICATE:
        raise HTTPException(status_code=409, detail="This document type cannot be reissued through activity issuance")
    activity = db.get(Activity, document.activity_id)
    if activity is None or activity.status == ActivityStatus.ARCHIVED or activity.template_id is None:
        raise HTTPException(status_code=409, detail="The source activity is no longer issuable")
    template = db.scalar(
        select(Template).where(
            Template.id == activity.template_id,
            Template.approved.is_(True),
            Template.archived.is_(False),
        )
    )
    if template is None:
        raise HTTPException(status_code=409, detail="An approved certificate template is required before reissue")
    if template.signature_handling is None:
        raise HTTPException(
            status_code=409,
            detail="The template requires an explicit retain or replace signature choice before reissue",
        )
    template_fields = db.scalars(
        select(TemplateField).where(TemplateField.template_id == template.id)
    ).all()
    field_names = {field.field_name for field in template_fields}
    missing_fields = missing_required_fields(field_names)
    if missing_fields:
        raise HTTPException(
            status_code=409,
            detail="Template is missing required fields: " + ", ".join(sorted(missing_fields)),
        )
    active_signatories = list(
        db.scalars(select(Signatory).where(Signatory.active.is_(True))).all()
    )
    available_signatories: dict[str, list[tuple[date, date | None]]] = defaultdict(list)
    for signatory in active_signatories:
        available_signatories[signatory.official_title].append(
            (signatory.effective_start_date, signatory.effective_end_date)
        )
    required_signatory_titles = required_titles()
    missing_signatories = missing_titles(required_signatory_titles, available_signatories, activity.activity_date)
    if missing_signatories:
        raise HTTPException(
            status_code=409,
            detail="Required signatories are unavailable: " + ", ".join(missing_signatories),
        )
    selected_signatories = select_effective_signatories(
        active_signatories, required_signatory_titles, activity.activity_date
    )
    if template.signature_handling == "replace":
        missing_signature_boxes = missing_signature_fields(template_fields, selected_signatories)
        if missing_signature_boxes:
            raise HTTPException(
                status_code=409,
                detail="Template is missing signature fields: " + ", ".join(missing_signature_boxes),
            )

    issue_date = datetime.now(EMC_TIMEZONE).date()
    document.status = DocumentStatus.SUPERSEDED
    replacement = reserve_document(
        db,
        student_id=document.student_id,
        activity_id=activity.id,
        template_id=template.id,
        document_type=document.document_type,
        issue_date=issue_date,
        render_values={
            "student_name": db.get(Student, document.student_id).full_name,
            "roll_number": db.get(Student, document.student_id).roll_number,
            "activity_name": activity.name,
            "activity_date": activity.activity_date,
            "issue_date": issue_date,
        },
        actor_admin_id=admin.id,
        version=document.version + 1,
        signatories=tuple(selected_signatories.values()),
    )
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="DOCUMENT_SUPERSEDED",
        entity_type="issued_document",
        entity_id=document.id,
        payload={"replacement_document_id": str(replacement.id), "replacement_version": replacement.version},
    )
    db.commit()
    return DocumentReissueResponse(
        superseded_document_id=document.id,
        replacement_document_id=replacement.id,
        issue_date=issue_date,
        version=replacement.version,
    )


def _reissue_leadership_document(
    db: Session, document: IssuedDocument, admin: Admin
) -> DocumentReissueResponse:
    if document.executive_membership_id is None or document.leadership_template_id is None:
        raise HTTPException(status_code=409, detail="The original leadership document snapshot is incomplete")
    try:
        values = json.loads(document.render_payload_json or "")
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=409, detail="The original leadership document data is unavailable") from error
    if not values:
        raise HTTPException(status_code=409, detail="The original leadership document data is unavailable")
    selected_signatories = tuple(
        db.scalars(
            select(Signatory)
            .join(DocumentSignatory, DocumentSignatory.signatory_id == Signatory.id)
            .where(DocumentSignatory.issued_document_id == document.id)
        ).all()
    )
    if not selected_signatories:
        raise HTTPException(status_code=409, detail="The original leadership signatory snapshot is unavailable")
    issue_date = datetime.now(EMC_TIMEZONE).date()
    values["issue_date"] = issue_date.isoformat()
    document.status = DocumentStatus.SUPERSEDED
    replacement = reserve_document(
        db,
        student_id=document.student_id,
        executive_membership_id=document.executive_membership_id,
        leadership_template_id=document.leadership_template_id,
        document_type=document.document_type,
        issue_date=issue_date,
        render_values=values,
        actor_admin_id=admin.id,
        version=document.version + 1,
        signatories=selected_signatories,
    )
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="DOCUMENT_SUPERSEDED",
        entity_type="issued_document",
        entity_id=document.id,
        payload={"replacement_document_id": str(replacement.id), "replacement_version": replacement.version},
    )
    db.commit()
    return DocumentReissueResponse(
        superseded_document_id=document.id,
        replacement_document_id=replacement.id,
        issue_date=issue_date,
        version=replacement.version,
    )
