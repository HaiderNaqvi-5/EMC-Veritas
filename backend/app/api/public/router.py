from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.domain import Activity, DocumentStatus, DocumentType, IssuedDocument, Student
from app.schemas.public import PublicDocument, StudentDocumentsResponse, VerificationResponse

router = APIRouter(prefix="/public", tags=["public"])

@router.get("/students/{roll_number}/documents", response_model=StudentDocumentsResponse)
def student_documents(roll_number: str, db: Session = Depends(get_db)) -> StudentDocumentsResponse:
    student = db.scalar(select(Student).where(Student.roll_number == roll_number.strip(), Student.active.is_(True)))
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
