from uuid import UUID, uuid4

import fitz
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.admin.dependencies import super_admin_required
from app.db.session import get_db
from app.models.domain import Admin, DocumentType, LeadershipTemplate, LeadershipTemplateField
from app.schemas.leadership_templates import (
    LeadershipDocumentType,
    LeadershipTemplateFieldsCreate,
    LeadershipTemplateResponse,
)
from app.services.audit import record_audit_event
from app.services.executive.constants import EXECUTIVE_ROLES
from app.services.executive.letters import (
    REQUIRED_LEADERSHIP_TEMPLATE_FIELDS,
    missing_leadership_template_fields,
)
from app.services.storage.supabase import SupabaseStorage
from app.services.templates.signature_choice import require_signature_choice
from app.services.templates.validation import ensure_pdf

router = APIRouter(prefix="/leadership-templates", tags=["leadership templates"])

_ALLOWED_DOCUMENT_TYPES = frozenset(
    {DocumentType.LEADERSHIP_RECOGNITION, DocumentType.END_OF_TENURE_APPRECIATION}
)
_ALLOWED_SIGNATURE_FIELDS = frozenset({"signature_president", "signature_dsa", "signature_hod"})
_ALLOWED_FIELD_NAMES = REQUIRED_LEADERSHIP_TEMPLATE_FIELDS | _ALLOWED_SIGNATURE_FIELDS


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
    document_type: LeadershipDocumentType = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(super_admin_required),
) -> LeadershipTemplate:
    normalized_role = role.strip()
    if normalized_role not in EXECUTIVE_ROLES:
        raise HTTPException(status_code=422, detail="Role must be an official EMC executive role")
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
    if db.scalar(
        select(LeadershipTemplateField.id).where(LeadershipTemplateField.leadership_template_id == template.id)
    ) is not None:
        raise HTTPException(status_code=409, detail="Leadership template fields are already configured")
    names = [field.field_name for field in payload.fields]
    if len(names) != len(set(names)):
        raise HTTPException(status_code=422, detail="Template field names must be unique")
    unsupported = set(names) - _ALLOWED_FIELD_NAMES
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
    missing = missing_leadership_template_fields(field_names)
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

    # Lock the role/type set so a concurrent replacement cannot leave two active templates.
    replacements = list(
        db.scalars(
            select(LeadershipTemplate)
            .where(
                LeadershipTemplate.role == template.role,
                LeadershipTemplate.document_type == template.document_type,
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
        payload={"replaced_template_ids": [str(item.id) for item in replacements if item.id != template.id]},
    )
    db.commit()
    db.refresh(template)
    return template


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
