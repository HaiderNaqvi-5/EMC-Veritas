from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.admin.dependencies import super_admin_required
from app.db.session import get_db
from app.models.domain import Admin, AdminRole, Student
from app.schemas.auth import AdminAccountCreate, AdminAccountResponse, AdminPasswordReset
from app.services.audit import record_audit_event
from app.services.auth import hash_password

router = APIRouter(prefix="/admins", tags=["admin-accounts"])


def _response(admin: Admin, student: Student) -> AdminAccountResponse:
    return AdminAccountResponse(
        id=admin.id,
        student_id=student.id,
        roll_number=student.roll_number,
        full_name=student.full_name,
        role=admin.role.value,
        active=admin.active,
        must_change_password=admin.must_change_password,
    )


def _admin_row(db: Session, admin_id: UUID) -> tuple[Admin, Student] | None:
    return db.execute(select(Admin, Student).join(Student, Admin.student_id == Student.id).where(Admin.id == admin_id)).first()


@router.get("", response_model=list[AdminAccountResponse])
def list_admins(
    _: Admin = Depends(super_admin_required), db: Session = Depends(get_db)
) -> list[AdminAccountResponse]:
    return [_response(admin, student) for admin, student in db.execute(select(Admin, Student).join(Student, Admin.student_id == Student.id).order_by(Student.roll_number)).all()]


@router.post("", response_model=AdminAccountResponse, status_code=status.HTTP_201_CREATED)
def create_admin(
    payload: AdminAccountCreate,
    actor: Admin = Depends(super_admin_required),
    db: Session = Depends(get_db),
) -> AdminAccountResponse:
    student = db.get(Student, payload.student_id)
    if student is None or not student.active:
        raise HTTPException(status_code=422, detail="An active student is required for an Admin account")
    account = Admin(
        student_id=student.id,
        role=AdminRole(payload.role),
        password_hash=hash_password(payload.temporary_password),
        active=True,
        must_change_password=True,
    )
    db.add(account)
    record_audit_event(
        db,
        actor_admin_id=actor.id,
        event_type="ADMIN_ACCOUNT_CREATED",
        entity_type="admin",
        entity_id=account.id,
        payload={"student_id": str(student.id), "role": account.role.value},
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="This student already has an Admin account") from error
    return _response(account, student)


@router.post("/{admin_id}/deactivate", response_model=AdminAccountResponse)
def deactivate_admin(
    admin_id: UUID,
    actor: Admin = Depends(super_admin_required),
    db: Session = Depends(get_db),
) -> AdminAccountResponse:
    if admin_id == actor.id:
        raise HTTPException(status_code=409, detail="A Super Admin cannot deactivate their own account")
    row = _admin_row(db, admin_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Admin account not found")
    account, student = row
    account.active = False
    record_audit_event(
        db,
        actor_admin_id=actor.id,
        event_type="ADMIN_ACCOUNT_DEACTIVATED",
        entity_type="admin",
        entity_id=account.id,
        payload={},
    )
    db.commit()
    return _response(account, student)


@router.post("/{admin_id}/reset-password", response_model=AdminAccountResponse)
def reset_admin_password(
    admin_id: UUID,
    payload: AdminPasswordReset,
    actor: Admin = Depends(super_admin_required),
    db: Session = Depends(get_db),
) -> AdminAccountResponse:
    row = _admin_row(db, admin_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Admin account not found")
    account, student = row
    if not account.active:
        raise HTTPException(status_code=409, detail="Inactive Admin accounts cannot be reset")
    account.password_hash = hash_password(payload.temporary_password)
    account.must_change_password = True
    record_audit_event(
        db,
        actor_admin_id=actor.id,
        event_type="ADMIN_PASSWORD_RESET",
        entity_type="admin",
        entity_id=account.id,
        payload={},
    )
    db.commit()
    return _response(account, student)
