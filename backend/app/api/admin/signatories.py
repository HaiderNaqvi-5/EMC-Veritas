from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.admin.dependencies import current_active_admin
from app.db.session import get_db
from app.models.domain import Admin, Signatory
from app.schemas.signatories import SignatoryResponse
from app.services.audit import record_audit_event
from app.services.signatures.image import prepare_signature_image
from app.services.storage.supabase import SupabaseStorage

router = APIRouter(prefix="/signatories", tags=["signatories"])
IMAGE_CONTENT_TYPES = {"image/png": ".png", "image/jpeg": ".jpg"}


def _signatory_or_404(db: Session, signatory_id: UUID) -> Signatory:
    signatory = db.get(Signatory, signatory_id)
    if signatory is None:
        raise HTTPException(status_code=404, detail="Signatory not found")
    return signatory


@router.post("", response_model=SignatoryResponse, status_code=status.HTTP_201_CREATED)
async def create_signatory(
    name: str = Form(..., min_length=1, max_length=255),
    official_title: str = Form(..., min_length=1, max_length=255),
    effective_start_date: date = Form(...),
    effective_end_date: date | None = Form(None),
    signature: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(current_active_admin),
) -> Signatory:
    if effective_end_date is not None and effective_end_date < effective_start_date:
        raise HTTPException(status_code=422, detail="Effective end date cannot precede start date")
    if signature.content_type not in IMAGE_CONTENT_TYPES:
        raise HTTPException(status_code=422, detail="Signature image must be PNG or JPEG")
    content = await signature.read()
    if not content:
        raise HTTPException(status_code=422, detail="Signature image cannot be empty")
    try:
        content = prepare_signature_image(content)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    identifier = uuid4()
    storage_key = str(Path("signatures") / f"{identifier}.png")
    try:
        SupabaseStorage().upload(storage_key, content, "image/png")
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Signature storage is temporarily unavailable") from error
    signatory = Signatory(
        id=identifier,
        name=name.strip(),
        official_title=official_title.strip(),
        signature_storage_key=storage_key,
        effective_start_date=effective_start_date,
        effective_end_date=effective_end_date,
        active=True,
    )
    db.add(signatory)
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="SIGNATORY_CREATED",
        entity_type="signatory",
        entity_id=signatory.id,
        payload={"official_title": signatory.official_title, "storage_key": storage_key},
    )
    db.commit()
    db.refresh(signatory)
    return signatory


@router.get("", response_model=list[SignatoryResponse])
def list_signatories(
    db: Session = Depends(get_db), admin: Admin = Depends(current_active_admin)
) -> list[Signatory]:
    return list(db.scalars(select(Signatory).order_by(Signatory.official_title, Signatory.effective_start_date)).all())


@router.post("/{signatory_id}/deactivate", response_model=SignatoryResponse)
def deactivate_signatory(
    signatory_id: UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(current_active_admin),
) -> Signatory:
    signatory = _signatory_or_404(db, signatory_id)
    signatory.active = False
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="SIGNATORY_DEACTIVATED",
        entity_type="signatory",
        entity_id=signatory.id,
        payload={},
    )
    db.commit()
    db.refresh(signatory)
    return signatory
