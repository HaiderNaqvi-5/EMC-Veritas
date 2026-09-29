from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.admin.dependencies import super_admin_required
from app.db.session import get_db
from app.models.domain import (
    Admin,
    EmailChangeRequest,
    EmailChangeRequestStatus,
    Student,
    StudentAccountTokenPurpose,
)
from app.schemas.auth import EmailRecoveryRequestResponse
from app.services.audit import record_audit_event
from app.services.email import send_student_activation
from app.services.student_accounts import approve_email_change, issue_token

router = APIRouter(prefix="/student-recovery", tags=["admin-student-recovery"])


def serialize(item: EmailChangeRequest, student: Student) -> EmailRecoveryRequestResponse:
    return EmailRecoveryRequestResponse(
        id=item.id, student_id=student.id, roll_number=student.roll_number,
        full_name=student.full_name, requested_email=item.requested_email,
        reason=item.reason, status=item.status.value, created_at=item.created_at,
    )


@router.get("", response_model=list[EmailRecoveryRequestResponse])
def pending_requests(_: Admin = Depends(super_admin_required), db: Session = Depends(get_db)) -> list[EmailRecoveryRequestResponse]:
    rows = db.execute(select(EmailChangeRequest, Student).join(Student, EmailChangeRequest.student_id == Student.id).where(EmailChangeRequest.status == EmailChangeRequestStatus.PENDING).order_by(EmailChangeRequest.created_at)).all()
    return [serialize(item, student) for item, student in rows]


@router.post("/{request_id}/approve", status_code=status.HTTP_204_NO_CONTENT)
def approve(request_id: str, admin: Admin = Depends(super_admin_required), db: Session = Depends(get_db)) -> Response:
    item = db.get(EmailChangeRequest, request_id)
    if item is None or item.status != EmailChangeRequestStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending recovery request not found")
    student = approve_email_change(db, item, admin.id)
    token = issue_token(db, student, StudentAccountTokenPurpose.ACTIVATION)
    record_audit_event(db, event_type="STUDENT_EMAIL_RECOVERY_APPROVED", entity_type="email_change_request", entity_id=item.id, payload={"student_id": str(student.id)}, actor_admin_id=admin.id)
    db.commit()
    send_student_activation(student.email, token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
