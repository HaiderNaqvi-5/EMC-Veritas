from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import EmcSession, SessionStatus
from app.schemas.operations import SessionCreate, SessionUpdate


def list_sessions(db: Session) -> list[EmcSession]:
    return list(db.scalars(select(EmcSession).order_by(EmcSession.start_date.desc())))


def create_session(db: Session, payload: SessionCreate) -> EmcSession:
    item = EmcSession(name=payload.name.strip(), start_date=payload.start_date, end_date=payload.end_date, status=SessionStatus.ACTIVE)
    db.add(item); db.flush()
    return item


def close_session(db: Session, item: EmcSession) -> EmcSession:
    item.status = SessionStatus.CLOSED
    db.flush()
    return item


def update_session(db: Session, item: EmcSession, payload: SessionUpdate) -> EmcSession:
    item.name = payload.name.strip()
    item.start_date = payload.start_date
    item.end_date = payload.end_date
    db.flush()
    return item
