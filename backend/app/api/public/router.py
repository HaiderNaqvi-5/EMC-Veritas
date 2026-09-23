from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.domain import Activity, DocumentStatus, DocumentType, IssuedDocument, Student
from app.schemas.public import PublicDocument, StudentDocumentsResponse

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
