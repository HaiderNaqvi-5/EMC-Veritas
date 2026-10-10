import json
import logging
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.admin.dependencies import current_active_admin, super_admin_required
from app.core.settings import settings
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
    ActivityCertificateRevokeResponse,
    ActivityIssueResponse,
    ActivityPreGenerationResponse,
    AdminDocumentResponse,
    DocumentPurgeResponse,
    DocumentReissueResponse,
)
from app.services.audit import record_audit_event
from app.services.documents.issuance import reserve_document
from app.services.documents.lifecycle import DocumentLifecycleError, generate_on_first_download
from app.services.signatures.availability import select_effective_signatories_for_fields
from app.services.signatures.rendering import (
    configured_signature_field_names,
    should_replace_signatures,
    signature_field_name,
)
from app.services.storage.supabase import SupabaseStorage
from app.services.templates.fields import missing_required_fields

router = APIRouter(prefix="/documents", tags=["documents"])
EMC_TIMEZONE = ZoneInfo("Asia/Karachi")
logger = logging.getLogger(__name__)


def _admin_document_response(
    document: IssuedDocument, student: Student, activity_name: str | None, template_name: str | None
) -> AdminDocumentResponse:
    return AdminDocumentResponse(
        id=document.id,
        verification_id=document.verification_id,
        student_id=student.id,
        student_name=student.full_name,
        roll_number=student.roll_number,
        activity_id=document.activity_id,
        document_type=document.document_type.value,
        context=activity_name or template_name or document.document_type.value.replace("_", " ").title(),
        issue_date=document.issue_date,
        status=document.status.value,
        version=document.version,
        storage_key=document.storage_key,
        sha256=document.sha256,
    )


def _signature_images_for_reserved_document(
    db: Session, document: IssuedDocument, storage: SupabaseStorage, download_cache: dict[str, bytes] | None = None
) -> dict[str, bytes]:
    rows = db.execute(
        select(DocumentSignatory, Signatory)
        .join(Signatory, DocumentSignatory.signatory_id == Signatory.id)
        .where(DocumentSignatory.issued_document_id == document.id)
    ).all()
    if not rows:
        raise DocumentLifecycleError("The document has no reserved signature snapshot")

    result = {}
    for snapshot, signatory in rows:
        key = signatory.signature_storage_key
        if download_cache is not None:
            if key not in download_cache:
                download_cache[key] = storage.download(key)
            result[signature_field_name(snapshot.official_title)] = download_cache[key]
        else:
            result[signature_field_name(snapshot.official_title)] = storage.download(key)
    return result


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
    if activity.status not in {ActivityStatus.READY, ActivityStatus.PUBLISHED}:
        raise HTTPException(
            status_code=409,
            detail="Only READY or PUBLISHED activities can issue participant certificates",
        )
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

    issue_date = activity.issue_date or datetime.now(EMC_TIMEZONE).date()
    selected_signatories = {}
    if should_replace_signatures(template.signature_handling, template_fields):
        signature_fields = configured_signature_field_names(template_fields)
        if not signature_fields:
            raise HTTPException(
                status_code=409,
                detail="A replace-signature template needs at least one signature_<title> field",
            )
        active_signatories = list(db.scalars(select(Signatory).where(Signatory.active.is_(True))).all())
        selected_signatories = select_effective_signatories_for_fields(
            active_signatories, signature_fields, issue_date
        )
        unavailable_fields = sorted(set(signature_fields) - set(selected_signatories))
        if unavailable_fields:
            raise HTTPException(
                status_code=409,
                detail="Configured signatories are unavailable for: " + ", ".join(unavailable_fields),
            )

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
    students = {
        student.id: student
        for student in db.scalars(select(Student).where(Student.id.in_(eligible_student_ids))).all()
    }
    issued_document_ids: list[UUID] = []
    skipped_student_ids: list[UUID] = []
    try:
        for student_id in eligible_student_ids:
            if student_id in existing_student_ids:
                skipped_student_ids.append(student_id)
                continue
            student = students.get(student_id)
            if student is None:
                raise HTTPException(status_code=409, detail="An eligible student could not be found")
            document = reserve_document(
                db,
                student_id=student_id,
                activity_id=activity.id,
                template_id=template.id,
                document_type=DocumentType.ACTIVITY_CERTIFICATE,
                issue_date=issue_date,
                render_values={
                    "student_name": student.full_name,
                    "roll_number": student.roll_number,
                    "activity_name": activity.name,
                    "activity_date": activity.activity_date,
                    "issue_date": issue_date,
                },
                actor_admin_id=admin.id,
                signatories=tuple(selected_signatories.values()),
            )
            issued_document_ids.append(document.id)
        activity.issue_date = issue_date
        # The first run publishes a READY activity. Later runs are deliberate:
        # participants may be added after publication, and existing valid
        # certificates are skipped above while the new participants receive
        # their first certificate.
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
        # Flush before committing so every database constraint is checked while
        # this request can still return a useful error and roll back cleanly.
        db.flush()
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Certificate publication failed for activity %s", activity.id)
        raise HTTPException(
            status_code=500,
            detail="Certificate publication failed and was rolled back. No certificate was issued.",
        ) from error
    return ActivityIssueResponse(
        activity_id=activity.id,
        issue_date=issue_date,
        issued_document_ids=issued_document_ids,
        skipped_student_ids=skipped_student_ids,
    )


@router.post("/activities/{activity_id}/pre-generate", response_model=ActivityPreGenerationResponse)
def pre_generate_activity_documents(
    activity_id: UUID,
    limit: int = 5,
    db: Session = Depends(get_db),
    admin: Admin = Depends(current_active_admin),
) -> ActivityPreGenerationResponse:
    """Render a small bounded batch before a public link is shared."""
    return _pre_generate_activity_document_batch(
        activity_id,
        document_type=DocumentType.ACTIVITY_CERTIFICATE,
        rendering_profile="default",
        audit_event_type="ACTIVITY_DOCUMENTS_PREGENERATED",
        limit=limit,
        db=db,
        admin=admin,
    )


@router.post(
    "/activities/{activity_id}/pre-generate-ec",
    response_model=ActivityPreGenerationResponse,
)
def pre_generate_ec_documents(
    activity_id: UUID,
    limit: int = 5,
    db: Session = Depends(get_db),
    admin: Admin = Depends(current_active_admin),
) -> ActivityPreGenerationResponse:
    """Render a bounded batch of issued EC certificates before students download."""
    return _pre_generate_activity_document_batch(
        activity_id,
        document_type=DocumentType.EXECUTIVE_COUNCIL_CERTIFICATE,
        rendering_profile="executive_council",
        audit_event_type="ACTIVITY_EC_DOCUMENTS_PREGENERATED",
        limit=limit,
        db=db,
        admin=admin,
    )


def _pre_generate_activity_document_batch(
    activity_id: UUID,
    *,
    document_type: DocumentType,
    rendering_profile: str,
    audit_event_type: str,
    limit: int,
    db: Session,
    admin: Admin,
) -> ActivityPreGenerationResponse:
    if limit < 1 or limit > 20:
        raise HTTPException(status_code=422, detail="Batch size must be between 1 and 20")
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    valid_documents = list(
        db.scalars(
            select(IssuedDocument)
            .where(
                IssuedDocument.activity_id == activity.id,
                IssuedDocument.document_type == document_type,
                IssuedDocument.status == DocumentStatus.VALID,
            )
            .order_by(IssuedDocument.created_at)
        ).all()
    )
    pending = [document for document in valid_documents if not document.storage_key][:limit]
    ready_before = len(valid_documents) - sum(1 for document in valid_documents if not document.storage_key)
    generated = 0
    failed_document_ids: list[UUID] = []
    storage = SupabaseStorage()

    # Cache external storage downloads (templates, signatures) during this batch
    # to prevent redundant network I/O across loop iterations.
    download_cache: dict[str, bytes] = {}

    for document in pending:
        document_id = document.id
        try:
            student = db.get(Student, document.student_id)
            template_id = document.template_id or (
                activity.template_id
                if document_type is DocumentType.ACTIVITY_CERTIFICATE
                else None
            )
            template = db.get(Template, template_id) if template_id is not None else None
            if student is None or template is None:
                raise DocumentLifecycleError("The issued document is missing its student or template")
            fields = list(db.scalars(select(TemplateField).where(TemplateField.template_id == template.id)).all())
            try:
                values = json.loads(document.render_payload_json or "")
            except json.JSONDecodeError as error:
                raise DocumentLifecycleError("The reserved certificate data is unavailable") from error
            if not values:
                if document_type is DocumentType.EXECUTIVE_COUNCIL_CERTIFICATE:
                    raise DocumentLifecycleError("The reserved EC certificate data is unavailable")
                values = {
                    "student_name": student.full_name,
                    "roll_number": student.roll_number,
                    "activity_name": activity.name,
                    "activity_date": activity.activity_date.isoformat(),
                    "issue_date": document.issue_date.isoformat(),
                }
            values["verification_id"] = document.verification_id

            if template.storage_key not in download_cache:
                download_cache[template.storage_key] = storage.download(template.storage_key)
            template_pdf = download_cache[template.storage_key]

            image_values = (
                _signature_images_for_reserved_document(db, document, storage, download_cache)
                if should_replace_signatures(template.signature_handling, fields)
                else None
            )
            generate_on_first_download(
                db,
                document=document,
                template_pdf=template_pdf,
                template_fields=fields,
                values=values,
                storage=storage,
                public_base_url=settings.public_app_url,
                actor_admin_id=admin.id,
                image_values=image_values,
                rendering_profile=rendering_profile,
            )
            db.commit()
            generated += 1
        except (DocumentLifecycleError, RuntimeError):
            db.rollback()
            failed_document_ids.append(document_id)
    ready = ready_before + generated
    total = len(valid_documents)
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type=audit_event_type,
        entity_type="activity",
        entity_id=activity.id,
        payload={
            "document_type": document_type.value,
            "generated_count": generated,
            "failed_document_ids": [str(item) for item in failed_document_ids],
        },
    )
    db.commit()
    return ActivityPreGenerationResponse(
        activity_id=activity.id,
        total_documents=total,
        ready_documents=ready,
        generated_documents=generated,
        remaining_documents=max(total - ready, 0),
        failed_document_ids=failed_document_ids,
    )


def _revoke_activity_certificates(
    db: Session,
    *,
    activity: Activity,
    admin: Admin,
    student_id: UUID | None = None,
) -> list[UUID]:
    """Revoke only currently valid certificates belonging to an activity."""
    query = select(IssuedDocument).where(
        IssuedDocument.activity_id == activity.id,
        IssuedDocument.document_type == DocumentType.ACTIVITY_CERTIFICATE,
        IssuedDocument.status == DocumentStatus.VALID,
    )
    if student_id is not None:
        query = query.where(IssuedDocument.student_id == student_id)
    documents = list(db.scalars(query).all())
    for document in documents:
        document.status = DocumentStatus.REVOKED
        record_audit_event(
            db,
            actor_admin_id=admin.id,
            event_type="DOCUMENT_REVOKED",
            entity_type="issued_document",
            entity_id=document.id,
            payload={
                "reason": "activity_certificate_revocation",
                "activity_id": str(activity.id),
                "verification_id": document.verification_id,
                "version": document.version,
            },
        )
    return [document.id for document in documents]


def _purge_documents(
    db: Session,
    *,
    documents: list[IssuedDocument],
    admin: Admin,
    scope: str,
    activity_id: UUID | None = None,
    student_id: UUID | None = None,
) -> list[UUID]:
    """Erase documents and their generated files after an explicit Super Admin action."""
    document_ids = [document.id for document in documents]
    storage_keys = [document.storage_key for document in documents if document.storage_key]
    if storage_keys:
        SupabaseStorage().delete_many(storage_keys)
    if document_ids:
        db.execute(delete(DocumentSignatory).where(DocumentSignatory.issued_document_id.in_(document_ids)))
        for document in documents:
            db.delete(document)
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="DOCUMENTS_PERMANENTLY_DELETED",
        entity_type=scope,
        entity_id=activity_id or student_id or "documents",
        payload={
            "deleted_count": len(document_ids),
            "deleted_document_ids": [str(document_id) for document_id in document_ids],
            "activity_id": str(activity_id) if activity_id else None,
            "student_id": str(student_id) if student_id else None,
        },
    )
    return document_ids


@router.post("/activities/{activity_id}/revoke", response_model=ActivityCertificateRevokeResponse)
def revoke_activity_certificates(
    activity_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(current_active_admin),
) -> ActivityCertificateRevokeResponse:
    """Revoke every currently valid activity certificate for one activity."""
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    revoked_document_ids = _revoke_activity_certificates(db, activity=activity, admin=admin)
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="ACTIVITY_CERTIFICATES_REVOKED",
        entity_type="activity",
        entity_id=activity.id,
        payload={"revoked_count": len(revoked_document_ids), "student_id": None},
    )
    db.commit()
    return ActivityCertificateRevokeResponse(
        activity_id=activity.id,
        revoked_document_ids=revoked_document_ids,
    )


@router.post(
    "/activities/{activity_id}/students/{student_id}/revoke",
    response_model=ActivityCertificateRevokeResponse,
)
def revoke_student_activity_certificates(
    activity_id: UUID,
    student_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(current_active_admin),
) -> ActivityCertificateRevokeResponse:
    """Revoke one student's currently valid certificate for one activity."""
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    revoked_document_ids = _revoke_activity_certificates(
        db,
        activity=activity,
        admin=admin,
        student_id=student_id,
    )
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="ACTIVITY_CERTIFICATES_REVOKED",
        entity_type="activity",
        entity_id=activity.id,
        payload={"revoked_count": len(revoked_document_ids), "student_id": str(student_id)},
    )
    db.commit()
    return ActivityCertificateRevokeResponse(
        activity_id=activity.id,
        student_id=student_id,
        revoked_document_ids=revoked_document_ids,
    )


@router.delete("/activities/{activity_id}/documents", response_model=DocumentPurgeResponse)
def permanently_delete_activity_certificates(
    activity_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> DocumentPurgeResponse:
    """Permanently erase every activity certificate, including revoked test records."""
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    documents = list(db.scalars(select(IssuedDocument).where(
        IssuedDocument.activity_id == activity.id,
        IssuedDocument.document_type == DocumentType.ACTIVITY_CERTIFICATE,
    )).all())
    deleted_document_ids = _purge_documents(
        db,
        documents=documents,
        admin=admin,
        scope="activity",
        activity_id=activity.id,
    )
    db.commit()
    return DocumentPurgeResponse(
        scope="activity",
        activity_id=activity.id,
        deleted_document_ids=deleted_document_ids,
    )


@router.delete("/students/{student_id}/documents", response_model=DocumentPurgeResponse)
def permanently_delete_student_documents(
    student_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> DocumentPurgeResponse:
    """Permanently erase all certificate and leadership-document history for one student."""
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    documents = list(db.scalars(select(IssuedDocument).where(
        IssuedDocument.student_id == student.id,
    )).all())
    deleted_document_ids = _purge_documents(
        db,
        documents=documents,
        admin=admin,
        scope="student",
        student_id=student.id,
    )
    db.commit()
    return DocumentPurgeResponse(
        scope="student",
        student_id=student.id,
        deleted_document_ids=deleted_document_ids,
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
    issue_date = datetime.now(EMC_TIMEZONE).date()
    selected_signatories = {}
    if should_replace_signatures(template.signature_handling, template_fields):
        signature_fields = configured_signature_field_names(template_fields)
        if not signature_fields:
            raise HTTPException(
                status_code=409,
                detail="A replace-signature template needs at least one signature_<title> field",
            )
        active_signatories = list(db.scalars(select(Signatory).where(Signatory.active.is_(True))).all())
        selected_signatories = select_effective_signatories_for_fields(
            active_signatories, signature_fields, issue_date
        )
        unavailable_fields = sorted(set(signature_fields) - set(selected_signatories))
        if unavailable_fields:
            raise HTTPException(
                status_code=409,
                detail="Configured signatories are unavailable for: " + ", ".join(unavailable_fields),
            )

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
