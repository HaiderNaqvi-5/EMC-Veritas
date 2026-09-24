from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.admin.students import require_admin
from app.db.session import get_db
from app.models.domain import (
    Activity,
    ActivityParticipant,
    ActivityStatus,
    DocumentStatus,
    DocumentType,
    IssuedDocument,
    Template,
)
from app.schemas.operations import (
    ActivityCreate,
    ActivityResponse,
    ActivityUpdate,
    ApprovedTemplateOption,
)
from app.services.activities import (
    add_participant,
    change_activity_status,
    create_activity,
    list_activities,
    participants,
    update_activity,
)
from app.services.audit import record_audit_event

router = APIRouter(prefix="/activities", tags=["admin-activities"])


class ParticipantCreate(BaseModel):
    student_id: UUID
    eligible: bool = True


class EligibilityChange(BaseModel):
    eligible: bool


class ActivityStatusChange(BaseModel):
    status: ActivityStatus


@router.get("", response_model=list[ActivityResponse])
def get_all(_: UUID = Depends(require_admin), db: Session = Depends(get_db)):
    return list_activities(db)


@router.get("/templates", response_model=list[ApprovedTemplateOption])
def list_approved_templates(
    _: UUID = Depends(require_admin), db: Session = Depends(get_db)
) -> list[Template]:
    return list(
        db.query(Template)
        .filter(Template.approved.is_(True), Template.archived.is_(False))
        .order_by(Template.name)
        .all()
    )


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create(payload: ActivityCreate, admin_id: UUID = Depends(require_admin), db: Session = Depends(get_db)):
    item = create_activity(db, payload, admin_id)
    record_audit_event(db, event_type="ACTIVITY_CREATED", entity_type="activity", entity_id=item.id, payload={}, actor_admin_id=admin_id)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{activity_id}", response_model=ActivityResponse)
def update(activity_id: UUID, payload: ActivityUpdate, admin_id: UUID = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(Activity, activity_id)
    if item is None:
        raise HTTPException(404, "Activity not found")
    update_activity(db, item, payload)
    record_audit_event(db, event_type="ACTIVITY_UPDATED", entity_type="activity", entity_id=item.id, payload={}, actor_admin_id=admin_id)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(activity_id: UUID, admin_id: UUID = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(Activity, activity_id)
    if item is None:
        raise HTTPException(404, "Activity not found")
    if db.scalar(select(IssuedDocument.id).where(IssuedDocument.activity_id == item.id)) is not None:
        raise HTTPException(409, "An activity with issued certificates cannot be deleted")
    db.query(ActivityParticipant).filter(ActivityParticipant.activity_id == item.id).delete(synchronize_session=False)
    record_audit_event(db, event_type="ACTIVITY_DELETED", entity_type="activity", entity_id=item.id, payload={"name": item.name}, actor_admin_id=admin_id)
    db.delete(item)
    db.commit()


@router.get("/{activity_id}/participants")
def get_participants(activity_id: UUID, _: UUID = Depends(require_admin), db: Session = Depends(get_db)):
    if db.get(Activity, activity_id) is None:
        raise HTTPException(404, "Activity not found")
    return participants(db, activity_id)


@router.post("/{activity_id}/participants", status_code=status.HTTP_201_CREATED)
def add(activity_id: UUID, payload: ParticipantCreate, admin_id: UUID = Depends(require_admin), db: Session = Depends(get_db)):
    if db.get(Activity, activity_id) is None:
        raise HTTPException(404, "Activity not found")
    try:
        item = add_participant(db, activity_id, payload.student_id, payload.eligible)
        record_audit_event(db, event_type="PARTICIPANT_ADDED", entity_type="activity_participant", entity_id=item.id, payload={"eligible": item.eligible}, actor_admin_id=admin_id)
        db.commit()
        return {"id": str(item.id), "student_id": str(item.student_id), "eligible": item.eligible}
    except LookupError:
        raise HTTPException(404, "Student not found")
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This student is already a participant")


@router.post("/{activity_id}/status", response_model=ActivityResponse)
def set_status(activity_id: UUID, payload: ActivityStatusChange, admin_id: UUID = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(Activity, activity_id)
    if item is None:
        raise HTTPException(404, "Activity not found")
    try:
        change_activity_status(item, payload.status)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    record_audit_event(db, event_type="ACTIVITY_STATUS_CHANGED", entity_type="activity", entity_id=item.id, payload={"status": item.status.value}, actor_admin_id=admin_id)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{activity_id}/participants/{participant_id}/eligibility")
def set_eligibility(activity_id: UUID, participant_id: UUID, payload: EligibilityChange, admin_id: UUID = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(ActivityParticipant, participant_id)
    if item is None or item.activity_id != activity_id:
        raise HTTPException(404, "Participant not found")
    item.eligible = payload.eligible
    record_audit_event(db, event_type="PARTICIPANT_ELIGIBILITY_CHANGED", entity_type="activity_participant", entity_id=item.id, payload={"eligible": item.eligible}, actor_admin_id=admin_id)
    if not item.eligible:
        documents = db.scalars(
            select(IssuedDocument).where(
                IssuedDocument.activity_id == activity_id,
                IssuedDocument.student_id == item.student_id,
                IssuedDocument.document_type == DocumentType.ACTIVITY_CERTIFICATE,
                IssuedDocument.status == DocumentStatus.VALID,
            )
        ).all()
        for document in documents:
            document.status = DocumentStatus.REVOKED
            record_audit_event(
                db,
                event_type="DOCUMENT_REVOKED",
                entity_type="issued_document",
                entity_id=document.id,
                payload={"reason": "participant_ineligible", "verification_id": document.verification_id},
                actor_admin_id=admin_id,
            )
    db.commit()
    return {"id": str(item.id), "student_id": str(item.student_id), "eligible": item.eligible}
