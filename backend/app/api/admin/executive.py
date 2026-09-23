from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.admin.students import require_admin
from app.db.session import get_db
from app.models.domain import (
    EmcSession,
    ExecutiveMembership,
    MembershipStatus,
    SessionStatus,
    Society,
    Student,
)
from app.schemas.operations import (
    ExecutiveMembershipCreate,
    ExecutiveMembershipResponse,
    ExecutiveMembershipUpdate,
    SocietyResponse,
)
from app.services.audit import record_audit_event
from app.services.executive.validation import validate_membership

router = APIRouter(prefix="/executive-memberships", tags=["executive memberships"])


def _response(row: tuple[ExecutiveMembership, Student, EmcSession, str | None, UUID | None]) -> ExecutiveMembershipResponse:
    membership, student, session, society_name, society_id = row
    return ExecutiveMembershipResponse(
        id=membership.id,
        student_id=student.id,
        student_name=student.full_name,
        roll_number=student.roll_number,
        session_id=session.id,
        session_name=session.name,
        society_id=society_id,
        society_name=society_name,
        role=membership.role,
        start_date=membership.start_date,
        end_date=membership.end_date,
        status=membership.status,
    )


def _membership_row(db: Session, membership_id: UUID) -> tuple[ExecutiveMembership, Student, EmcSession, str | None, UUID | None] | None:
    return db.execute(
        select(ExecutiveMembership, Student, EmcSession, Society.name, Society.id)
        .join(Student, ExecutiveMembership.student_id == Student.id)
        .join(EmcSession, ExecutiveMembership.session_id == EmcSession.id)
        .outerjoin(Society, ExecutiveMembership.society_id == Society.id)
        .where(ExecutiveMembership.id == membership_id)
    ).first()


def _validate_membership_inputs(
    db: Session, *, role: str, society_id: UUID | None, start_date, end_date
) -> None:
    society_name = None
    if society_id is not None:
        society = db.get(Society, society_id)
        if society is None or not society.active:
            raise HTTPException(status_code=422, detail="Society must be one of the active EMC societies")
        society_name = society.name
    try:
        validate_membership(role, society_name)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if end_date is not None and end_date < start_date:
        raise HTTPException(status_code=422, detail="Membership end date cannot be before its start date")


@router.get("/societies", response_model=list[SocietyResponse])
def list_societies(_: UUID = Depends(require_admin), db: Session = Depends(get_db)) -> list[Society]:
    return list(db.scalars(select(Society).where(Society.active.is_(True)).order_by(Society.name)).all())


@router.get("", response_model=list[ExecutiveMembershipResponse])
def list_memberships(
    session_id: UUID | None = None,
    _: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[ExecutiveMembershipResponse]:
    query = (
        select(ExecutiveMembership, Student, EmcSession, Society.name, Society.id)
        .join(Student, ExecutiveMembership.student_id == Student.id)
        .join(EmcSession, ExecutiveMembership.session_id == EmcSession.id)
        .outerjoin(Society, ExecutiveMembership.society_id == Society.id)
        .order_by(EmcSession.start_date.desc(), ExecutiveMembership.role, Student.full_name)
    )
    if session_id is not None:
        query = query.where(ExecutiveMembership.session_id == session_id)
    return [_response(row) for row in db.execute(query).all()]


@router.post("", response_model=ExecutiveMembershipResponse, status_code=status.HTTP_201_CREATED)
def create_membership(
    payload: ExecutiveMembershipCreate,
    admin_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ExecutiveMembershipResponse:
    student = db.get(Student, payload.student_id)
    session = db.get(EmcSession, payload.session_id)
    if student is None or not student.active:
        raise HTTPException(status_code=422, detail="An active student is required")
    if session is None:
        raise HTTPException(status_code=404, detail="EMC session not found")
    if session.status is not SessionStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Memberships can only be created in an active session")
    _validate_membership_inputs(
        db,
        role=payload.role,
        society_id=payload.society_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    membership = ExecutiveMembership(**payload.model_dump())
    db.add(membership)
    record_audit_event(
        db,
        actor_admin_id=admin_id,
        event_type="EXECUTIVE_MEMBERSHIP_CREATED",
        entity_type="executive_membership",
        entity_id=membership.id,
        payload={"role": membership.role, "status": membership.status.value},
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This student already has an Executive Council membership in the session, or a Society Head tenure overlaps",
        ) from error
    row = _membership_row(db, membership.id)
    assert row is not None
    return _response(row)


@router.put("/{membership_id}", response_model=ExecutiveMembershipResponse)
def update_membership(
    membership_id: UUID,
    payload: ExecutiveMembershipUpdate,
    admin_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ExecutiveMembershipResponse:
    membership = db.get(ExecutiveMembership, membership_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Executive membership not found")
    session = db.get(EmcSession, membership.session_id)
    if session is None or session.status is not SessionStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Closed-session memberships cannot be changed")
    values = payload.model_dump(exclude_unset=True)
    role = values.get("role", membership.role)
    society_id = values.get("society_id", membership.society_id)
    start_date = values.get("start_date", membership.start_date)
    end_date = values.get("end_date", membership.end_date)
    _validate_membership_inputs(db, role=role, society_id=society_id, start_date=start_date, end_date=end_date)
    for key, value in values.items():
        setattr(membership, key, value)
    record_audit_event(
        db,
        actor_admin_id=admin_id,
        event_type="EXECUTIVE_MEMBERSHIP_UPDATED",
        entity_type="executive_membership",
        entity_id=membership.id,
        payload={"changed_fields": sorted(values)},
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Society Head tenure overlaps an existing membership") from error
    row = _membership_row(db, membership.id)
    assert row is not None
    return _response(row)


@router.post("/{membership_id}/complete", response_model=ExecutiveMembershipResponse)
def complete_membership(
    membership_id: UUID,
    admin_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ExecutiveMembershipResponse:
    membership = db.get(ExecutiveMembership, membership_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Executive membership not found")
    session = db.get(EmcSession, membership.session_id)
    if session is None or session.status is not SessionStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Closed-session memberships cannot be changed")
    membership.status = MembershipStatus.COMPLETED
    membership.end_date = membership.end_date or session.end_date
    record_audit_event(
        db,
        actor_admin_id=admin_id,
        event_type="EXECUTIVE_MEMBERSHIP_COMPLETED",
        entity_type="executive_membership",
        entity_id=membership.id,
        payload={"end_date": membership.end_date.isoformat()},
    )
    db.commit()
    row = _membership_row(db, membership.id)
    assert row is not None
    return _response(row)


@router.post("/{membership_id}/remove", response_model=ExecutiveMembershipResponse)
def remove_membership(
    membership_id: UUID,
    admin_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ExecutiveMembershipResponse:
    membership = db.get(ExecutiveMembership, membership_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Executive membership not found")
    session = db.get(EmcSession, membership.session_id)
    if session is None or session.status is not SessionStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Closed-session memberships cannot be changed")
    membership.status = MembershipStatus.REMOVED
    membership.end_date = membership.end_date or session.end_date
    record_audit_event(
        db,
        actor_admin_id=admin_id,
        event_type="EXECUTIVE_MEMBERSHIP_REMOVED",
        entity_type="executive_membership",
        entity_id=membership.id,
        payload={"end_date": membership.end_date.isoformat()},
    )
    db.commit()
    row = _membership_row(db, membership.id)
    assert row is not None
    return _response(row)
