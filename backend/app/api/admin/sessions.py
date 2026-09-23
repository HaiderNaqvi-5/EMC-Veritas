from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.admin.students import require_admin
from app.db.session import get_db
from app.models.domain import EmcSession
from app.schemas.operations import SessionCreate, SessionResponse, SessionUpdate
from app.services.audit import record_audit_event
from app.services.executive.issuance import (
    RecognitionPrerequisiteError,
    reserve_session_recognition,
)
from app.services.sessions import close_session, create_session, list_sessions, update_session

router = APIRouter(prefix="/sessions", tags=["admin-sessions"])

@router.get("", response_model=list[SessionResponse])
def get_sessions(_: UUID = Depends(require_admin), db: Session = Depends(get_db)) -> list[EmcSession]: return list_sessions(db)

@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def add_session(payload: SessionCreate, admin_id: UUID = Depends(require_admin), db: Session = Depends(get_db)) -> EmcSession:
    try:
        item = create_session(db, payload); record_audit_event(db, event_type="SESSION_CREATED", entity_type="session", entity_id=item.id, payload={"name": item.name}, actor_admin_id=admin_id); db.commit(); db.refresh(item); return item
    except IntegrityError:
        db.rollback(); raise HTTPException(status_code=409, detail="Only one ACTIVE session is allowed; close the current session first")

@router.post("/{session_id}/close", response_model=SessionResponse)
def close(session_id: str, admin_id: UUID = Depends(require_admin), db: Session = Depends(get_db)) -> EmcSession:
    item = db.get(EmcSession, session_id)
    if item is None: raise HTTPException(status_code=404, detail="Session not found")
    try:
        close_session(db, item)
        reserve_session_recognition(db, session=item, actor_admin_id=admin_id)
        record_audit_event(db, event_type="SESSION_CLOSED", entity_type="session", entity_id=item.id, payload={}, actor_admin_id=admin_id)
        db.commit(); db.refresh(item); return item
    except RecognitionPrerequisiteError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.put("/{session_id}", response_model=SessionResponse)
def edit_session(session_id: str, payload: SessionUpdate, admin_id: UUID = Depends(require_admin), db: Session = Depends(get_db)) -> EmcSession:
    item = db.get(EmcSession, session_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        update_session(db, item, payload)
        record_audit_event(db, event_type="SESSION_UPDATED", entity_type="session", entity_id=item.id, payload={}, actor_admin_id=admin_id)
        db.commit(); db.refresh(item)
        return item
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Session dates or name conflict with an existing record")
