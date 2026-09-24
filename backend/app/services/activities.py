from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import Activity, ActivityParticipant, ActivityStatus, Student
from app.schemas.operations import ActivityCreate, ActivityUpdate


def list_activities(db: Session) -> list[Activity]: return list(db.scalars(select(Activity).order_by(Activity.activity_date.desc())))
def create_activity(db: Session, payload: ActivityCreate, admin_id) -> Activity:
    item = Activity(**payload.model_dump(), created_by_admin_id=admin_id, status=ActivityStatus.DRAFT); db.add(item); db.flush(); return item
def update_activity(db: Session, item: Activity, payload: ActivityUpdate) -> Activity:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.flush()
    return item


def change_activity_status(item: Activity, target: ActivityStatus) -> Activity:
    allowed = {
        ActivityStatus.DRAFT: ActivityStatus.READY,
        ActivityStatus.PUBLISHED: ActivityStatus.ARCHIVED,
    }
    if target != allowed.get(item.status):
        raise ValueError(f"Activity status can only progress from {item.status.value}")
    item.status = target
    return item
def participants(db: Session, activity_id) -> list[ActivityParticipant]: return list(db.scalars(select(ActivityParticipant).where(ActivityParticipant.activity_id == activity_id)))
def add_participant(db: Session, activity_id, student_id, eligible: bool = True) -> ActivityParticipant:
    if db.get(Student, student_id) is None: raise LookupError("Student not found")
    item = ActivityParticipant(activity_id=activity_id, student_id=student_id, eligible=eligible); db.add(item); db.flush(); return item
