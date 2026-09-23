from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.admin.dependencies import current_active_admin
from app.db.session import get_db
from app.models.domain import (
    Admin,
    EmcSession,
    ExecutiveMembership,
    MembershipStatus,
    Society,
    Student,
)
from app.services.audit import record_audit_event
from app.services.executive.constants import EXECUTIVE_ROLES

router = APIRouter(prefix="/executive-memberships", tags=["executive memberships"])


class MembershipCreate(BaseModel):
    student_id: UUID
    session_id: UUID
    society_id: UUID | None = None
    role: str
    start_date: date
    end_date: date | None = None
    status: MembershipStatus = MembershipStatus.ACTIVE

    @model_validator(mode="after")
    def validate_role_and_dates(self):
        if self.role not in EXECUTIVE_ROLES:
            raise ValueError("Role must be an official EMC executive role")
        if self.role == "Society Head" and self.society_id is None:
            raise ValueError("Society Head requires a society")
        if self.role != "Society Head" and self.society_id is not None:
            raise ValueError("Only Society Head may have a society")
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("End date cannot precede start date")
        return self


class MembershipUpdate(BaseModel):
    end_date: date | None = None
    status: MembershipStatus


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    session_id: UUID
    society_id: UUID | None
    role: str
    start_date: date
    end_date: date | None
    status: MembershipStatus


@router.get("", response_model=list[MembershipResponse])
def list_memberships(_: Admin = Depends(current_active_admin), db: Session = Depends(get_db)) -> list[ExecutiveMembership]:
    return list(db.scalars(select(ExecutiveMembership).order_by(ExecutiveMembership.start_date.desc())).all())


@router.post("", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
def create_membership(payload: MembershipCreate, admin: Admin = Depends(current_active_admin), db: Session = Depends(get_db)) -> ExecutiveMembership:
    if db.get(Student, payload.student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    if db.get(EmcSession, payload.session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if payload.society_id is not None and db.get(Society, payload.society_id) is None:
        raise HTTPException(status_code=404, detail="Society not found")
    membership = ExecutiveMembership(**payload.model_dump())
    db.add(membership)
    try:
        db.flush()
        record_audit_event(db, actor_admin_id=admin.id, event_type="EXECUTIVE_MEMBERSHIP_CREATED", entity_type="executive_membership", entity_id=membership.id, payload={"role": membership.role, "status": membership.status.value})
        db.commit(); db.refresh(membership)
        return membership
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="This membership conflicts with an existing Council appointment") from error


@router.patch("/{membership_id}", response_model=MembershipResponse)
def update_membership(membership_id: UUID, payload: MembershipUpdate, admin: Admin = Depends(current_active_admin), db: Session = Depends(get_db)) -> ExecutiveMembership:
    membership = db.get(ExecutiveMembership, membership_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Executive membership not found")
    if payload.end_date is not None and payload.end_date < membership.start_date:
        raise HTTPException(status_code=422, detail="End date cannot precede start date")
    membership.end_date = payload.end_date
    membership.status = payload.status
    try:
        record_audit_event(db, actor_admin_id=admin.id, event_type="EXECUTIVE_MEMBERSHIP_UPDATED", entity_type="executive_membership", entity_id=membership.id, payload={"status": membership.status.value})
        db.commit(); db.refresh(membership)
        return membership
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="This membership conflicts with an existing Council appointment") from error
