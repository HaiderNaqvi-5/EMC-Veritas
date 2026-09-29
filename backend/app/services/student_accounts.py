"""Security-critical student account helpers.

Tokens are random, short-lived, single-use, and only their SHA-256 digest is
persisted.  The caller is responsible for delivering the raw token by email.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import (
    EmailChangeRequest,
    EmailChangeRequestStatus,
    Student,
    StudentAccount,
    StudentAccountToken,
    StudentAccountTokenPurpose,
)
from app.services.auth import hash_password, hasher
from app.services.students import normalize_roll_number

TOKEN_TTL_MINUTES = 15


def mask_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    local, domain = email.rsplit("@", 1)
    return f"{local[:1]}{'•' * max(3, len(local) - 1)}@{domain}"


def issue_token(db: Session, student: Student, purpose: StudentAccountTokenPurpose) -> str:
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    db.add(StudentAccountToken(
        student_id=student.id,
        purpose=purpose,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(minutes=TOKEN_TTL_MINUTES),
    ))
    return raw_token


def consume_token(db: Session, raw_token: str, purpose: StudentAccountTokenPurpose) -> Student | None:
    digest = hashlib.sha256(raw_token.encode()).hexdigest()
    token = db.scalar(select(StudentAccountToken).where(
        StudentAccountToken.token_hash == digest,
        StudentAccountToken.purpose == purpose,
        StudentAccountToken.used_at.is_(None),
    ))
    if token is None or token.expires_at <= datetime.now(UTC):
        return None
    student = db.get(Student, token.student_id)
    if student is None or not student.active:
        return None
    token.used_at = datetime.now(UTC)
    return student


def activate_account(db: Session, student: Student, password: str) -> StudentAccount:
    account = db.scalar(select(StudentAccount).where(StudentAccount.student_id == student.id))
    if account is None:
        account = StudentAccount(student_id=student.id)
        db.add(account)
    account.password_hash = hash_password(password)
    account.activated_at = datetime.now(UTC)
    student.email_verified_at = account.activated_at
    return account


def authenticate_student(db: Session, roll_number: str, password: str) -> Student | None:
    student = db.scalar(select(Student).where(Student.roll_number == normalize_roll_number(roll_number), Student.active.is_(True)))
    if student is None:
        return None
    account = db.scalar(select(StudentAccount).where(StudentAccount.student_id == student.id, StudentAccount.active.is_(True)))
    if account is None or not account.password_hash or account.activated_at is None:
        return None
    try:
        hasher.verify(account.password_hash, password)
    except VerifyMismatchError:
        return None
    return student


def request_email_change(db: Session, student: Student, requested_email: str, reason: str) -> EmailChangeRequest:
    request = EmailChangeRequest(student_id=student.id, requested_email=requested_email.strip().lower(), reason=reason.strip())
    db.add(request)
    return request


def approve_email_change(db: Session, request: EmailChangeRequest, admin_id) -> Student:
    student = db.get(Student, request.student_id)
    if student is None:
        raise ValueError("Student record no longer exists")
    request.status = EmailChangeRequestStatus.APPROVED
    request.reviewed_by_admin_id = admin_id
    request.reviewed_at = datetime.now(UTC)
    student.email = request.requested_email
    student.email_verified_at = None
    return student
