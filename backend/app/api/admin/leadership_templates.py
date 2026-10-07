from datetime import datetime
from io import BytesIO
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import fitz
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.admin.dependencies import super_admin_required
from app.core.settings import settings
from app.db.session import get_db
from app.models.domain import (
    Admin,
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
from app.schemas.leadership_templates import (
    LeadershipDocumentType,
    LeadershipLetterIssueResponse,
    LeadershipTemplateAnalysisResponse,
    LeadershipTemplateAssignment,
    LeadershipTemplateFieldsCreate,
    LeadershipTemplatePreviewRequest,
    LeadershipTemplateResponse,
)
from app.schemas.templates import DetectedTemplateFieldResponse
from app.services.audit import record_audit_event
from app.services.documents.issuance import reserve_document
from app.services.documents.lifecycle import DocumentLifecycleError, generate_on_first_download
from app.services.documents.qr import verification_url
from app.services.documents.rendering import CertificateRenderingError, render_certificate
from app.services.executive.constants import EXECUTIVE_ROLES
from app.services.executive.letters import (
    REQUIRED_LEADERSHIP_TEMPLATE_FIELDS,
    leadership_fields_for_rendering,
    leadership_letter_values,
    missing_leadership_template_fields,
    required_leadership_template_fields,
)
from app.services.signatures.availability import select_effective_signatories_for_fields
from app.services.signatures.rendering import configured_signature_field_names
from app.services.storage.supabase import SupabaseStorage
from app.services.templates.analysis import (
    analyze_pdf_text,
    detect_leadership_placeholders,
    has_signature_like_content,
)
from app.services.templates.signature_choice import require_signature_choice
from app.services.templates.validation import ensure_pdf

router = APIRouter(prefix="/leadership-templates", tags=["leadership templates"])
EMC_TIMEZONE = ZoneInfo("Asia/Karachi")

_ALLOWED_DOCUMENT_TYPES = frozenset(
    {DocumentType.LEADERSHIP_RECOGNITION, DocumentType.END_OF_TENURE_APPRECIATION}
)


def _is_allowed_field_name(field_name: str) -> bool:
    """Allow the letter fields plus any explicitly named signature slot.

    Signatory titles are configured by an administrator, so Leadership
    templates cannot be restricted to a fixed President/DSA/HOD list.
    """
    return field_name in REQUIRED_LEADERSHIP_TEMPLATE_FIELDS or field_name.startswith("signature_")


def _template_or_404(db: Session, template_id: UUID) -> LeadershipTemplate:
    template = db.get(LeadershipTemplate, template_id)
    if template is None or template.archived:
        raise HTTPException(status_code=404, detail="Leadership template not found")
    return template


def _document_type(value: LeadershipDocumentType) -> DocumentType:
    document_type = DocumentType(value)
    if document_type not in _ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported leadership document type")
    return document_type


def _restore_detected_fields_for_empty_template(
    db: Session, template: LeadershipTemplate, template_pdf: bytes
) -> list[LeadershipTemplateField]:
    """Recover tag positions for legacy drafts that have no saved fields.

    Older leadership-template uploads could show detected boxes in the editor
    without persisting them. A preview should recover those exact visible tags
    instead of incorrectly reporting that every field is missing.
    """
    detected = [field for field in detect_leadership_placeholders(template_pdf) if _is_allowed_field_name(field.field_name)]
    names = {field.field_name for field in detected}
    missing = missing_leadership_template_fields(names, template.role)
    if missing:
        raise HTTPException(status_code=422, detail="Template is missing fields: " + ", ".join(sorted(missing)))
    for field in detected:
        db.add(
            LeadershipTemplateField(
                leadership_template_id=template.id,
                field_name=field.field_name,
                page_number=field.page_number,
                x=field.x,
                y=field.y,
                width=field.width,
                height=field.height,
            )
        )
    # Templates without explicit signature tags keep the signatures embedded
    # in their PDF, which is the safe default for a recovered draft.
    template.signature_handling = template.signature_handling or "retain"
    db.commit()
    return list(
        db.scalars(
            select(LeadershipTemplateField).where(LeadershipTemplateField.leadership_template_id == template.id)
        ).all()
    )


@router.get("", response_model=list[LeadershipTemplateResponse])
def list_leadership_templates(
    db: Session = Depends(get_db), admin: Admin = Depends(super_admin_required)
) -> list[LeadershipTemplate]:
    return list(
        db.scalars(
            select(LeadershipTemplate)
            .where(LeadershipTemplate.archived.is_(False))
            .order_by(LeadershipTemplate.role, LeadershipTemplate.document_type, LeadershipTemplate.created_at.desc())
        ).all()
    )


@router.post("/upload", response_model=LeadershipTemplateResponse, status_code=status.HTTP_201_CREATED)
async def upload_leadership_template(
    name: str = Form(..., min_length=1, max_length=255),
    role: str = Form(..., min_length=1, max_length=80),
    executive_membership_id: UUID = Form(...),
    document_type: LeadershipDocumentType = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> LeadershipTemplate:
    normalized_role = role.strip()
    if normalized_role not in EXECUTIVE_ROLES:
        raise HTTPException(status_code=422, detail="Role must be an official EMC executive role")
    membership = db.get(ExecutiveMembership, executive_membership_id)
    if membership is None:
        raise HTTPException(status_code=422, detail="Choose a valid Executive Council membership")
    if membership.role != normalized_role:
        raise HTTPException(status_code=422, detail="The selected membership does not match the template role")
    ensure_pdf(file.filename or "", file.content_type)
    content = await file.read()
    try:
        fitz.open(stream=content, filetype="pdf").close()
    except fitz.FileDataError as error:
        raise HTTPException(status_code=422, detail="Uploaded template is not a readable PDF") from error

    template = LeadershipTemplate(
        id=uuid4(),
        name=name.strip(),
        role=normalized_role,
        executive_membership_id=membership.id,
        document_type=_document_type(document_type),
        storage_key=f"leadership-templates/{uuid4()}.pdf",
    )
    try:
        SupabaseStorage().upload(template.storage_key, content, "application/pdf")
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Template storage is temporarily unavailable") from error
    db.add(template)
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="LEADERSHIP_TEMPLATE_UPLOADED",
        entity_type="leadership_template",
        entity_id=template.id,
        payload={"name": template.name, "role": template.role, "document_type": template.document_type.value},
    )
    db.commit()
    db.refresh(template)
    return template


@router.get("/{template_id}/analysis", response_model=LeadershipTemplateAnalysisResponse)
def analyze_leadership_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> LeadershipTemplateAnalysisResponse:
    template = _template_or_404(db, template_id)
    try:
        pdf_bytes = SupabaseStorage().download(template.storage_key)
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = document.page_count
        document.close()
        analysis = analyze_pdf_text(pdf_bytes)
        detected_fields = detect_leadership_placeholders(pdf_bytes)
    except (RuntimeError, fitz.FileDataError) as error:
        raise HTTPException(status_code=503, detail="Template analysis is temporarily unavailable") from error
    return LeadershipTemplateAnalysisResponse(
        page_count=page_count,
        extracted_text=analysis.pages,
        ocr_used=analysis.ocr_used,
        ocr_required=analysis.ocr_required,
        signature_content_detected=has_signature_like_content(analysis.pages),
        # Detect the actual leadership-letter token locations rather than
        # falling back to arbitrary editor coordinates.
        detected_fields=[
            DetectedTemplateFieldResponse(**field.__dict__)
            for field in detected_fields
            if _is_allowed_field_name(field.field_name)
        ],
    )


@router.get("/{template_id}/pages/{page_number}")
def leadership_template_page_image(
    template_id: UUID,
    page_number: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> StreamingResponse:
    """Render the source page used by the leadership field-placement preview."""
    template = _template_or_404(db, template_id)
    try:
        pdf_bytes = SupabaseStorage().download(template.storage_key)
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        if page_number < 1 or page_number > document.page_count:
            document.close()
            raise HTTPException(status_code=404, detail="Leadership template page not found")
        image = document[page_number - 1].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        document.close()
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Template storage is temporarily unavailable") from error
    return StreamingResponse(BytesIO(image.tobytes("png")), media_type="image/png")


@router.post("/{template_id}/fields", response_model=LeadershipTemplateResponse)
def configure_leadership_template_fields(
    template_id: UUID,
    payload: LeadershipTemplateFieldsCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> LeadershipTemplate:
    template = _template_or_404(db, template_id)
    if template.active:
        raise HTTPException(status_code=409, detail="Active templates are immutable; upload a replacement")
    # A draft is editable. Replacing its saved placement lets an admin correct
    # a detector result before activation without having to upload another PDF.
    db.execute(
        delete(LeadershipTemplateField).where(LeadershipTemplateField.leadership_template_id == template.id)
    )
    names = [field.field_name for field in payload.fields]
    if len(names) != len(set(names)):
        raise HTTPException(status_code=422, detail="Template field names must be unique")
    unsupported = {name for name in names if not _is_allowed_field_name(name)}
    if unsupported:
        raise HTTPException(
            status_code=422,
            detail="Unsupported leadership template fields: " + ", ".join(sorted(unsupported)),
        )
    for field in payload.fields:
        db.add(LeadershipTemplateField(leadership_template_id=template.id, **field.model_dump()))
    try:
        template.signature_handling = require_signature_choice(payload.signature_handling)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="LEADERSHIP_TEMPLATE_FIELDS_CONFIGURED",
        entity_type="leadership_template",
        entity_id=template.id,
        payload={"fields": names, "signature_handling": template.signature_handling},
    )
    db.commit()
    db.refresh(template)
    return template


@router.post("/{template_id}/preview")
def preview_leadership_template(
    template_id: UUID,
    payload: LeadershipTemplatePreviewRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> StreamingResponse:
    template = _template_or_404(db, template_id)
    membership = db.get(ExecutiveMembership, payload.membership_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Executive membership not found")
    if membership.role != template.role:
        raise HTTPException(status_code=422, detail="The selected membership role does not match this template")
    if (
        template.executive_membership_id is not None
        and membership.id != template.executive_membership_id
    ):
        raise HTTPException(status_code=422, detail="This template is assigned to a different Executive member")
    student = db.get(Student, membership.student_id)
    session = db.get(EmcSession, membership.session_id)
    society_name = (
        db.scalar(select(Society.name).where(Society.id == membership.society_id))
        if membership.society_id is not None
        else None
    )
    if student is None or session is None:
        raise HTTPException(status_code=409, detail="The selected membership lacks required student or session data")
    fields = list(
        db.scalars(
            select(LeadershipTemplateField).where(LeadershipTemplateField.leadership_template_id == template.id)
        ).all()
    )
    missing = missing_leadership_template_fields({field.field_name for field in fields}, template.role)
    template_pdf: bytes | None = None
    if missing and not fields:
        try:
            template_pdf = SupabaseStorage().download(template.storage_key)
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail="Template storage is temporarily unavailable") from error
        fields = _restore_detected_fields_for_empty_template(db, template, template_pdf)
        missing = missing_leadership_template_fields({field.field_name for field in fields}, template.role)
    if missing:
        raise HTTPException(status_code=422, detail="Template is missing fields: " + ", ".join(sorted(missing)))
    end_date = membership.end_date or session.end_date
    values = leadership_letter_values(
        student_name=student.full_name,
        roll_number=student.roll_number,
        role=membership.role,
        society_name=society_name,
        role_start_date=membership.start_date,
        role_end_date=end_date,
        session_name=session.name,
        issue_date=session.end_date,
    )
    # Previews are not issued documents, so use a clear non-verifiable marker.
    # Issued leadership letters receive their immutable real ID at download
    # time from the reserved document record.
    values["verification_id"] = "PREVIEW"
    image_values: dict[str, bytes] | None = None
    try:
        storage = SupabaseStorage()
        template_pdf = template_pdf or storage.download(template.storage_key)
        if template.signature_handling == "replace":
            signatories = list(db.scalars(select(Signatory).where(Signatory.active.is_(True))).all())
            # A preview must reflect the fields that this particular PDF
            # actually requests. It must never impose role-policy titles such
            # as President or DSA on a template that only contains HOD.
            selected = select_effective_signatories_for_fields(
                signatories, configured_signature_field_names(fields), end_date
            )
            image_values = {
                field_name: storage.download(signatory.signature_storage_key)
                for field_name, signatory in selected.items()
            }
        output = render_certificate(
            template_pdf,
            leadership_fields_for_rendering(fields),
            values,
            verification_url=verification_url(settings.public_app_url, "PREVIEW"),
            watermark="PREVIEW",
            image_values=image_values,
            required_field_names=required_leadership_template_fields(template.role),
        )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Template storage is temporarily unavailable") from error
    except CertificateRenderingError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return StreamingResponse(
        BytesIO(output),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="EMC-leadership-template-preview.pdf"'},
    )


@router.post("/{template_id}/activate", response_model=LeadershipTemplateResponse)
def activate_leadership_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> LeadershipTemplate:
    template = _template_or_404(db, template_id)
    field_names = set(
        db.scalars(
            select(LeadershipTemplateField.field_name).where(
                LeadershipTemplateField.leadership_template_id == template.id
            )
        ).all()
    )
    missing = missing_leadership_template_fields(field_names, template.role)
    if missing:
        raise HTTPException(
            status_code=422,
            detail="Required leadership fields are missing: " + ", ".join(sorted(missing)),
        )
    if template.signature_handling is None:
        raise HTTPException(
            status_code=422,
            detail="Choose whether to retain or replace sample signatures before activation",
        )

    # Lock only this recipient/type slot. Activating one Society Head's letter
    # must not deactivate another Society Head's independently designed letter.
    replacements = list(
        db.scalars(
            select(LeadershipTemplate)
            .where(
                LeadershipTemplate.role == template.role,
                LeadershipTemplate.document_type == template.document_type,
                LeadershipTemplate.executive_membership_id == template.executive_membership_id,
                LeadershipTemplate.archived.is_(False),
                LeadershipTemplate.active.is_(True),
            )
            .with_for_update()
        ).all()
    )
    for replacement in replacements:
        replacement.active = False
    db.flush()
    template.active = True
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="LEADERSHIP_TEMPLATE_ACTIVATED",
        entity_type="leadership_template",
        entity_id=template.id,
        payload={
            "executive_membership_id": str(template.executive_membership_id),
            "replaced_template_ids": [str(item.id) for item in replacements if item.id != template.id],
        },
    )
    db.commit()
    db.refresh(template)
    return template


@router.post("/{template_id}/assignment", response_model=LeadershipTemplateResponse)
def assign_leadership_template(
    template_id: UUID,
    payload: LeadershipTemplateAssignment,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> LeadershipTemplate:
    template = _template_or_404(db, template_id)
    membership = db.get(ExecutiveMembership, payload.membership_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Executive membership not found")
    if membership.role != template.role:
        raise HTTPException(status_code=422, detail="The selected membership role does not match this template")

    # Preserve the active state while moving a legacy role-wide template into
    # the recipient's slot. Any previous active template in that exact slot is
    # safely deactivated first.
    replacements: list[LeadershipTemplate] = []
    was_active = template.active
    if was_active:
        replacements = list(
            db.scalars(
                select(LeadershipTemplate)
                .where(
                    LeadershipTemplate.id != template.id,
                    LeadershipTemplate.executive_membership_id == membership.id,
                    LeadershipTemplate.document_type == template.document_type,
                    LeadershipTemplate.archived.is_(False),
                    LeadershipTemplate.active.is_(True),
                )
                .with_for_update()
            ).all()
        )
        for replacement in replacements:
            replacement.active = False
        template.active = False
        db.flush()
    template.executive_membership_id = membership.id
    template.active = was_active
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="LEADERSHIP_TEMPLATE_ASSIGNED",
        entity_type="leadership_template",
        entity_id=template.id,
        payload={
            "executive_membership_id": str(membership.id),
            "replaced_template_ids": [str(item.id) for item in replacements],
        },
    )
    db.commit()
    db.refresh(template)
    return template


@router.post("/{template_id}/issue", response_model=LeadershipLetterIssueResponse)
def issue_leadership_letter(
    template_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> LeadershipLetterIssueResponse:
    template = _template_or_404(db, template_id)
    if not template.active:
        raise HTTPException(status_code=409, detail="Activate this template before issuing its letter")
    if template.executive_membership_id is None:
        raise HTTPException(status_code=409, detail="Assign this template to a specific Executive member first")
    membership = db.get(ExecutiveMembership, template.executive_membership_id)
    if membership is None or membership.status is MembershipStatus.REMOVED:
        raise HTTPException(status_code=409, detail="The assigned Executive membership is unavailable")
    if (
        template.document_type is DocumentType.END_OF_TENURE_APPRECIATION
        and membership.status is not MembershipStatus.COMPLETED
    ):
        raise HTTPException(status_code=409, detail="Complete the membership before issuing an end-of-tenure letter")
    existing = db.scalar(
        select(IssuedDocument.id).where(
            IssuedDocument.executive_membership_id == membership.id,
            IssuedDocument.document_type == template.document_type,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="This letter has already been issued to this member")
    student = db.get(Student, membership.student_id)
    session = db.get(EmcSession, membership.session_id)
    if student is None or not student.active or session is None:
        raise HTTPException(status_code=409, detail="The membership lacks an active student or EMC session")
    fields = list(
        db.scalars(
            select(LeadershipTemplateField).where(
                LeadershipTemplateField.leadership_template_id == template.id
            )
        ).all()
    )
    missing = missing_leadership_template_fields(
        {field.field_name for field in fields}, membership.role
    )
    if missing:
        raise HTTPException(
            status_code=422,
            detail="Required leadership fields are missing: " + ", ".join(sorted(missing)),
        )
    issue_date = datetime.now(EMC_TIMEZONE).date()
    role_end_date = membership.end_date or session.end_date
    society_name = (
        db.scalar(select(Society.name).where(Society.id == membership.society_id))
        if membership.society_id is not None
        else None
    )
    signatories: tuple[Signatory, ...] = ()
    if template.signature_handling == "replace":
        available = list(db.scalars(select(Signatory).where(Signatory.active.is_(True))).all())
        requested_fields = configured_signature_field_names(fields)
        selected = select_effective_signatories_for_fields(
            available, requested_fields, role_end_date
        )
        missing_signatures = sorted(set(requested_fields) - set(selected))
        if missing_signatures:
            raise HTTPException(
                status_code=409,
                detail="Required signatories are unavailable: " + ", ".join(sorted(missing_signatures)),
            )
        signatories = tuple(selected.values())
    render_values = leadership_letter_values(
        student_name=student.full_name,
        roll_number=student.roll_number,
        role=membership.role,
        society_name=society_name,
        role_start_date=membership.start_date,
        role_end_date=role_end_date,
        session_name=session.name,
        issue_date=issue_date,
    )
    document = reserve_document(
        db,
        student_id=student.id,
        executive_membership_id=membership.id,
        leadership_template_id=template.id,
        document_type=template.document_type,
        issue_date=issue_date,
        render_values=render_values,
        actor_admin_id=admin.id,
        signatories=signatories,
    )
    # Generate and cache the immutable PDF while the administrator issues it.
    # Student downloads should retrieve a ready Storage object instead of
    # paying the PDF-rendering cost on their first click.
    try:
        storage = SupabaseStorage()
        template_pdf = storage.download(template.storage_key)
        image_values = None
        if template.signature_handling == "replace":
            image_values = {
                field_name: storage.download(signatory.signature_storage_key)
                for field_name, signatory in selected.items()
            }
        generate_on_first_download(
            db,
            document=document,
            template_pdf=template_pdf,
            template_fields=leadership_fields_for_rendering(fields),
            values=render_values,
            storage=storage,
            public_base_url=settings.public_app_url,
            actor_admin_id=admin.id,
            image_values=image_values,
            required_field_names=required_leadership_template_fields(membership.role),
        )
    except RuntimeError as error:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="The letter could not be prepared in document storage. Please try issuing it again.",
        ) from error
    except DocumentLifecycleError as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="INDIVIDUAL_LEADERSHIP_LETTER_ISSUED",
        entity_type="issued_document",
        entity_id=document.id,
        payload={"template_id": str(template.id), "membership_id": str(membership.id)},
    )
    db.commit()
    return LeadershipLetterIssueResponse(
        document_id=document.id,
        verification_id=document.verification_id,
        document_type=document.document_type.value,
        issue_date=document.issue_date,
    )


@router.post("/{template_id}/deactivate", response_model=LeadershipTemplateResponse)
def deactivate_leadership_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> LeadershipTemplate:
    template = _template_or_404(db, template_id)
    if template.active:
        template.active = False
        record_audit_event(
            db,
            actor_admin_id=admin.id,
            event_type="LEADERSHIP_TEMPLATE_DEACTIVATED",
            entity_type="leadership_template",
            entity_id=template.id,
            payload={},
        )
        db.commit()
        db.refresh(template)
    return template


@router.post("/{template_id}/archive", response_model=LeadershipTemplateResponse)
def archive_leadership_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> LeadershipTemplate:
    template = _template_or_404(db, template_id)
    template.active = False
    template.archived = True
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="LEADERSHIP_TEMPLATE_ARCHIVED",
        entity_type="leadership_template",
        entity_id=template.id,
        payload={},
    )
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_leadership_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> None:
    """Remove a draft/test template from the editor without breaking issued letters.

    This deliberately archives rather than physically removes the row: issued
    documents retain their immutable reference to the template used to create
    them, while the deleted template immediately disappears from the UI.
    """
    template = _template_or_404(db, template_id)
    template.active = False
    template.archived = True
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="LEADERSHIP_TEMPLATE_DELETED",
        entity_type="leadership_template",
        entity_id=template.id,
        payload={"name": template.name},
    )
    db.commit()
