import json
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.session import get_db
from app.models.domain import (
    Activity,
    DocumentSignatory,
    DocumentStatus,
    DocumentType,
    IssuedDocument,
    LeadershipTemplate,
    LeadershipTemplateField,
    Signatory,
    Student,
    Template,
    TemplateField,
)
from app.schemas.public import PublicDocument, StudentDocumentsResponse, VerificationResponse
from app.services.documents.lifecycle import DocumentLifecycleError, generate_on_first_download
from app.services.executive.letters import REQUIRED_LEADERSHIP_TEMPLATE_FIELDS
from app.services.signatures.rendering import signature_field_name
from app.services.storage.supabase import SupabaseStorage
from app.services.students import normalize_roll_number

router = APIRouter(prefix="/public", tags=["public"])


def _signature_images_for_document(
    db: Session, document: IssuedDocument, storage: SupabaseStorage
) -> dict[str, bytes]:
    rows = db.execute(
        select(DocumentSignatory, Signatory)
        .join(Signatory, DocumentSignatory.signatory_id == Signatory.id)
        .where(DocumentSignatory.issued_document_id == document.id)
    ).all()
    if not rows:
        raise DocumentLifecycleError("The document has no reserved signature snapshot")
    return {
        signature_field_name(snapshot.official_title): storage.download(signatory.signature_storage_key)
        for snapshot, signatory in rows
    }

@router.get("/students/{roll_number}/documents", response_model=StudentDocumentsResponse)
def student_documents(roll_number: str, db: Session = Depends(get_db)) -> StudentDocumentsResponse:
    student = db.scalar(select(Student).where(func.upper(Student.roll_number) == normalize_roll_number(roll_number), Student.active.is_(True)))
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    rows = db.execute(
        select(IssuedDocument, Activity.name, Activity.activity_date)
        .outerjoin(Activity, IssuedDocument.activity_id == Activity.id)
        .where(IssuedDocument.student_id == student.id, IssuedDocument.status == DocumentStatus.VALID)
        .order_by(IssuedDocument.issue_date.desc())
    ).all()
    activity_certificates: list[PublicDocument] = []
    leadership_recognition: list[PublicDocument] = []
    for document, activity_name, activity_date in rows:
        item = PublicDocument(
            id=document.id,
            document_type=document.document_type.value,
            title=activity_name or document.document_type.value.replace("_", " ").title(),
            activity_date=activity_date,
            issue_date=document.issue_date,
            status=document.status.value,
        )
        (activity_certificates if document.document_type == DocumentType.ACTIVITY_CERTIFICATE else leadership_recognition).append(item)
    return StudentDocumentsResponse(
        full_name=student.full_name,
        roll_number=student.roll_number,
        activity_certificates=activity_certificates,
        leadership_recognition=leadership_recognition,
    )


@router.get("/verify/{verification_id}", response_model=VerificationResponse)
def verify_document(verification_id: str, db: Session = Depends(get_db)) -> VerificationResponse:
    row = db.execute(
        select(IssuedDocument, Student, Activity.name, Activity.activity_date)
        .join(Student, IssuedDocument.student_id == Student.id)
        .outerjoin(Activity, IssuedDocument.activity_id == Activity.id)
        .where(IssuedDocument.verification_id == verification_id.strip())
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Verification record not found")
    document, student, activity_name, activity_date = row
    return VerificationResponse(
        verified=document.status == DocumentStatus.VALID,
        status=document.status.value,
        verification_id=document.verification_id,
        full_name=student.full_name,
        roll_number=student.roll_number,
        document_type=document.document_type.value,
        context=activity_name or document.document_type.value.replace("_", " ").title(),
        activity_date=activity_date,
        issue_date=document.issue_date,
    )


@router.get("/documents/{document_id}/download")
def download_document(document_id: UUID, db: Session = Depends(get_db)) -> StreamingResponse:
    row = db.execute(
        select(IssuedDocument, Student, Activity)
        .join(Student, IssuedDocument.student_id == Student.id)
        .outerjoin(Activity, IssuedDocument.activity_id == Activity.id)
        .where(IssuedDocument.id == document_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    document, student, activity = row
    if document.status != DocumentStatus.VALID:
        raise HTTPException(status_code=410, detail="This document is no longer available for download")
    leadership_template_id = getattr(document, "leadership_template_id", None)
    if leadership_template_id is not None:
        template = db.scalar(select(LeadershipTemplate).where(LeadershipTemplate.id == leadership_template_id))
        if template is None:
            raise HTTPException(status_code=409, detail="The reserved leadership template is unavailable")
        fields = db.scalars(
            select(LeadershipTemplateField).where(
                LeadershipTemplateField.leadership_template_id == template.id
            )
        ).all()
        try:
            values = json.loads(getattr(document, "render_payload_json", "") or "")
        except (AttributeError, json.JSONDecodeError) as error:
            raise HTTPException(status_code=409, detail="The reserved leadership document data is unavailable") from error
        values["verification_id"] = document.verification_id
        required_field_names = REQUIRED_LEADERSHIP_TEMPLATE_FIELDS
    else:
        template_id = getattr(document, "template_id", None) or (
            activity.template_id if activity is not None else None
        )
        if template_id is None:
            raise HTTPException(status_code=409, detail="No certificate template is assigned to this document")
        template = db.scalar(select(Template).where(Template.id == template_id))
        if template is None:
            raise HTTPException(status_code=409, detail="The assigned certificate template is unavailable")
        fields = db.scalars(select(TemplateField).where(TemplateField.template_id == template.id)).all()
        raw_values = getattr(document, "render_payload_json", None)
        try:
            values = json.loads(raw_values) if raw_values else {}
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=409, detail="The reserved certificate data is unavailable") from error
        if not values:
            if activity is None:
                raise HTTPException(status_code=409, detail="The reserved certificate data is unavailable")
            values = {
                "student_name": student.full_name,
                "roll_number": student.roll_number,
                "activity_name": activity.name,
                "activity_date": activity.activity_date,
                "issue_date": document.issue_date,
            }
        values["verification_id"] = document.verification_id
        required_field_names = None
    try:
        storage = SupabaseStorage()
        template_pdf = storage.download(template.storage_key)
        image_values = (
            _signature_images_for_document(db, document, storage)
            if getattr(template, "signature_handling", "retain") == "replace"
            else None
        )
        output = generate_on_first_download(
            db,
            document=document,
            template_pdf=template_pdf,
            template_fields=fields,
            values=values,
            storage=storage,
            public_base_url=settings.public_app_url,
            image_values=image_values,
            required_field_names=required_field_names,
        )
        db.commit()
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Document storage is temporarily unavailable") from error
    except DocumentLifecycleError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error

    filename = f"EMC-{document.verification_id}.pdf"
    return StreamingResponse(
        BytesIO(output),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
