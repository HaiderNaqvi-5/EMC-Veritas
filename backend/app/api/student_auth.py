from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.domain import Student, StudentAccount, StudentAccountTokenPurpose
from app.schemas.auth import (
    StudentAccountRequest,
    StudentActivationConfirm,
    StudentActivationHint,
    StudentActivationLookup,
    StudentLoginRequest,
    StudentRecoveryRequest,
    StudentSessionResponse,
)
from app.services.audit import record_audit_event
from app.services.email import send_student_activation
from app.services.student_accounts import (
    activate_account,
    authenticate_student,
    consume_token,
    issue_token,
    mask_email,
    request_email_change,
)
from app.services.students import normalize_roll_number

router = APIRouter(prefix="/student-auth", tags=["student-auth"])


def session_response(request: Request, db: Session) -> StudentSessionResponse:
    raw_id = request.session.get("student_id")
    if not raw_id:
        return StudentSessionResponse(authenticated=False)
    try:
        student = db.get(Student, UUID(raw_id))
    except (TypeError, ValueError):
        request.session.clear()
        return StudentSessionResponse(authenticated=False)
    if student is None or not student.active:
        request.session.clear()
        return StudentSessionResponse(authenticated=False)
    return StudentSessionResponse(authenticated=True, full_name=student.full_name, roll_number=student.roll_number)


@router.post("/activation-email-hint", response_model=StudentActivationHint)
@limiter.limit("5/hour")
def activation_email_hint(payload: StudentActivationLookup, request: Request, db: Session = Depends(get_db)) -> StudentActivationHint:
    student = db.scalar(select(Student).where(Student.roll_number == normalize_roll_number(payload.roll_number), Student.active.is_(True)))
    # The name is a second roster factor. A non-match deliberately returns the
    # same empty result as an unknown or ineligible record.
    if student is None or student.full_name.casefold().strip() != payload.full_name.casefold().strip():
        return StudentActivationHint()
    return StudentActivationHint(email_hint=mask_email(student.email))


@router.post("/request-activation", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/hour")
def request_activation(payload: StudentAccountRequest, request: Request, db: Session = Depends(get_db)) -> Response:
    student = db.scalar(select(Student).where(Student.roll_number == normalize_roll_number(payload.roll_number), Student.active.is_(True)))
    # Always return the same response to prevent roll-number or email enumeration.
    if student is not None and student.email:
        token = issue_token(db, student, StudentAccountTokenPurpose.ACTIVATION)
        record_audit_event(db, event_type="STUDENT_ACTIVATION_REQUESTED", entity_type="student", entity_id=student.id, payload={})
        db.commit()
        send_student_activation(student.email, token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/activate", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/hour")
def confirm_activation(payload: StudentActivationConfirm, request: Request, db: Session = Depends(get_db)) -> Response:
    student = consume_token(db, payload.token, StudentAccountTokenPurpose.ACTIVATION)
    if student is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This activation link is invalid or has expired")
    activate_account(db, student, payload.password)
    record_audit_event(db, event_type="STUDENT_ACCOUNT_ACTIVATED", entity_type="student", entity_id=student.id, payload={})
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/request-password-reset", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/hour")
def request_password_reset(payload: StudentAccountRequest, request: Request, db: Session = Depends(get_db)) -> Response:
    student = db.scalar(select(Student).where(Student.roll_number == normalize_roll_number(payload.roll_number), Student.active.is_(True)))
    if student is not None and student.email:
        account = db.scalar(select(StudentAccount).where(StudentAccount.student_id == student.id, StudentAccount.active.is_(True)))
        if account is not None and account.activated_at is not None:
            token = issue_token(db, student, StudentAccountTokenPurpose.PASSWORD_RESET)
            record_audit_event(db, event_type="STUDENT_PASSWORD_RESET_REQUESTED", entity_type="student", entity_id=student.id, payload={})
            db.commit()
            send_student_activation(student.email, token, reset=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/hour")
def reset_password(payload: StudentActivationConfirm, request: Request, db: Session = Depends(get_db)) -> Response:
    student = consume_token(db, payload.token, StudentAccountTokenPurpose.PASSWORD_RESET)
    if student is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or has expired")
    activate_account(db, student, payload.password)
    record_audit_event(db, event_type="STUDENT_PASSWORD_RESET", entity_type="student", entity_id=student.id, payload={})
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/login", response_model=StudentSessionResponse)
@limiter.limit("10/minute")
def login(payload: StudentLoginRequest, request: Request, db: Session = Depends(get_db)) -> StudentSessionResponse:
    student = authenticate_student(db, payload.roll_number, payload.password)
    if student is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid student credentials")
    request.session.clear()
    request.session["student_id"] = str(student.id)
    record_audit_event(db, event_type="STUDENT_LOGIN", entity_type="student", entity_id=student.id, payload={})
    db.commit()
    return session_response(request, db)


@router.post("/recovery-requests", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/day")
def recovery_request(payload: StudentRecoveryRequest, request: Request, db: Session = Depends(get_db)) -> Response:
    student = db.scalar(select(Student).where(Student.roll_number == normalize_roll_number(payload.roll_number), Student.active.is_(True)))
    if student is not None:
        change = request_email_change(db, student, payload.requested_email, payload.reason)
        record_audit_event(db, event_type="STUDENT_EMAIL_RECOVERY_REQUESTED", entity_type="email_change_request", entity_id=change.id, payload={})
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    request.session.pop("student_id", None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/session", response_model=StudentSessionResponse)
def session(request: Request, db: Session = Depends(get_db)) -> StudentSessionResponse:
    return session_response(request, db)
