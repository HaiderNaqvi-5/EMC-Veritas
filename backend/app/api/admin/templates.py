from io import BytesIO
from uuid import UUID, uuid4

import fitz
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.admin.dependencies import current_active_admin, super_admin_required
from app.core.settings import settings
from app.db.session import get_db
from app.models.domain import Activity, Admin, Student, Template, TemplateField
from app.schemas.templates import (
    TemplateAnalysisResponse,
    TemplateFieldsCreate,
    TemplatePreviewRequest,
    TemplateResponse,
)
from app.services.audit import record_audit_event
from app.services.documents.qr import verification_url
from app.services.documents.rendering import CertificateRenderingError, render_certificate
from app.services.storage.supabase import SupabaseStorage
from app.services.templates.analysis import analyze_pdf_text, has_signature_like_content
from app.services.templates.fields import missing_required_fields
from app.services.templates.signature_choice import require_signature_choice
from app.services.templates.validation import ensure_pdf

router = APIRouter(prefix="/templates", tags=["templates"])


def _template_or_404(db: Session, template_id: UUID) -> Template:
    template = db.get(Template, template_id)
    if template is None or template.archived:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.get("", response_model=list[TemplateResponse])
def list_templates(
    db: Session = Depends(get_db), admin: Admin = Depends(super_admin_required)
) -> list[Template]:
    return list(db.scalars(select(Template).where(Template.archived.is_(False)).order_by(Template.created_at.desc())).all())


@router.post("/upload", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def upload_template(
    name: str = Form(..., min_length=1, max_length=255),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> Template:
    ensure_pdf(file.filename or "", file.content_type)
    content = await file.read()
    try:
        fitz.open(stream=content, filetype="pdf").close()
    except fitz.FileDataError as error:
        raise HTTPException(status_code=422, detail="Uploaded template is not a readable PDF") from error
    template = Template(id=uuid4(), name=name.strip(), storage_key=f"templates/{uuid4()}.pdf")
    try:
        SupabaseStorage().upload(template.storage_key, content, "application/pdf")
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Template storage is temporarily unavailable") from error
    db.add(template)
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="TEMPLATE_UPLOADED",
        entity_type="template",
        entity_id=template.id,
        payload={"name": template.name, "storage_key": template.storage_key},
    )
    db.commit()
    db.refresh(template)
    return template


@router.get("/{template_id}/analysis", response_model=TemplateAnalysisResponse)
def analyze_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> TemplateAnalysisResponse:
    template = _template_or_404(db, template_id)
    try:
        pdf_bytes = SupabaseStorage().download(template.storage_key)
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = document.page_count
        document.close()
        analysis = analyze_pdf_text(pdf_bytes)
    except (RuntimeError, fitz.FileDataError) as error:
        raise HTTPException(status_code=503, detail="Template analysis is temporarily unavailable") from error
    return TemplateAnalysisResponse(
        page_count=page_count,
        extracted_text=analysis.pages,
        ocr_used=analysis.ocr_used,
        ocr_required=analysis.ocr_required,
        signature_content_detected=has_signature_like_content(analysis.pages),
    )


@router.get("/{template_id}/source")
def template_source(
    template_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> StreamingResponse:
    """Serve the private source PDF only to the field editor; never expose Storage URLs."""
    template = _template_or_404(db, template_id)
    try:
        pdf_bytes = SupabaseStorage().download(template.storage_key)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Template storage is temporarily unavailable") from error
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="EMC-template-source.pdf"'},
    )


@router.post("/{template_id}/fields", response_model=TemplateResponse)
def configure_template_fields(
    template_id: UUID,
    payload: TemplateFieldsCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> Template:
    template = _template_or_404(db, template_id)
    if template.approved:
        raise HTTPException(status_code=409, detail="Approved templates are immutable; upload a new version")
    if db.scalar(select(TemplateField.id).where(TemplateField.template_id == template.id)) is not None:
        raise HTTPException(status_code=409, detail="Template fields are already configured")
    try:
        signature_handling = require_signature_choice(payload.signature_handling)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    names = [field.field_name for field in payload.fields]
    if len(names) != len(set(names)):
        raise HTTPException(status_code=422, detail="Template field names must be unique")
    for field in payload.fields:
        db.add(TemplateField(template_id=template.id, **field.model_dump()))
    template.signature_handling = signature_handling
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="TEMPLATE_FIELDS_CONFIGURED",
        entity_type="template",
        entity_id=template.id,
        payload={"fields": names, "signature_handling": signature_handling},
    )
    db.commit()
    db.refresh(template)
    return template


@router.post("/{template_id}/preview")
def preview_template(
    template_id: UUID,
    payload: TemplatePreviewRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(current_active_admin),
) -> StreamingResponse:
    template = _template_or_404(db, template_id)
    student = db.get(Student, payload.student_id)
    activity = db.get(Activity, payload.activity_id)
    if student is None or not student.active:
        raise HTTPException(status_code=404, detail="Student not found")
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    fields = db.scalars(select(TemplateField).where(TemplateField.template_id == template.id)).all()
    try:
        template_pdf = SupabaseStorage().download(template.storage_key)
        output = render_certificate(
            template_pdf,
            fields,
            {
                "student_name": student.full_name,
                "roll_number": student.roll_number,
                "activity_name": activity.name,
                "activity_date": activity.activity_date,
            },
            verification_url=verification_url(settings.public_app_url, "PREVIEW"),
            watermark="PREVIEW",
        )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Template storage is temporarily unavailable") from error
    except CertificateRenderingError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return StreamingResponse(
        BytesIO(output),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="EMC-template-preview.pdf"'},
    )


@router.post("/{template_id}/approve", response_model=TemplateResponse)
def approve_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> Template:
    template = _template_or_404(db, template_id)
    names = set(db.scalars(select(TemplateField.field_name).where(TemplateField.template_id == template.id)).all())
    missing = missing_required_fields(names)
    if missing:
        raise HTTPException(
            status_code=422,
            detail="Required template fields are missing: " + ", ".join(sorted(missing)),
        )
    if template.signature_handling is None:
        raise HTTPException(
            status_code=422,
            detail="Choose whether to retain or replace sample signatures before approval",
        )
    template.approved = True
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="TEMPLATE_APPROVED",
        entity_type="template",
        entity_id=template.id,
        payload={},
    )
    db.commit()
    db.refresh(template)
    return template
