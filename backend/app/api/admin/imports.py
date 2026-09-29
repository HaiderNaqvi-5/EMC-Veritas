import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.admin.dependencies import current_active_admin
from app.db.session import get_db
from app.models.domain import Admin, Student
from app.schemas.operations import ImportCommit, StudentCreate
from app.services.audit import record_audit_event
from app.services.imports import import_activity_participants, participant_export, preview_students
from app.services.students import create_student, normalize_roll_number

router=APIRouter(prefix="/imports",tags=["admin-imports"])

logger = logging.getLogger(__name__)

# Participant rosters are small spreadsheets; 10 MB is generous headroom
# while keeping one request from exhausting worker memory.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


async def _bounded_read(file: UploadFile) -> bytes:
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Upload exceeds the 10 MB limit")
    return content
@router.post("/students/preview")
async def preview(file: UploadFile=File(...), _: Admin=Depends(current_active_admin), db: Session=Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".xlsx"): raise HTTPException(400,"Only .xlsx files are accepted")
    try: return preview_students(db, await _bounded_read(file))
    except ValueError as error:
        logger.warning("student import preview rejected: %s", type(error).__name__)
        raise HTTPException(400, "The file could not be processed. Check the format and try again.")

@router.get("/activities/{activity_id}/participants/export")
def export(activity_id: UUID, _: Admin=Depends(current_active_admin), db: Session=Depends(get_db)):
    try: content=participant_export(db,activity_id)
    except LookupError: raise HTTPException(404,"Activity not found")
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition":"attachment; filename=Export Participants.xlsx"})

@router.post("/activities/{activity_id}/participants/import")
async def import_participants(activity_id: UUID, file: UploadFile=File(...), admin: Admin=Depends(current_active_admin), db: Session=Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".xlsx"): raise HTTPException(400, "Only .xlsx files are accepted")
    try: result = import_activity_participants(db, activity_id, await _bounded_read(file))
    except LookupError: raise HTTPException(404, "Activity not found")
    except ValueError as error:
        logger.warning("activity participant import rejected: %s", type(error).__name__)
        raise HTTPException(400, "The file could not be processed. Check the format and try again.")
    record_audit_event(db, actor_admin_id=admin.id, event_type="ACTIVITY_PARTICIPANTS_IMPORTED", entity_type="activity", entity_id=activity_id, payload=result)
    db.commit(); return result

@router.post("/students/commit")
def commit(payload: ImportCommit, admin: Admin=Depends(current_active_admin), db: Session=Depends(get_db)):
    created=0; skipped=0
    for row in payload.rows:
        canonical_roll_number = normalize_roll_number(row.roll_number)
        current=db.query(Student).filter(Student.roll_number == canonical_roll_number).one_or_none()
        if current is None:
            create_student(
                db,
                StudentCreate(roll_number=canonical_roll_number, full_name=row.full_name.strip(), email=row.email),
            )
            created += 1
        elif current.full_name == row.full_name.strip() and not current.email and row.email:
            # Legacy student rows can be enrolled once from the verified roster;
            # an already-set email is never overwritten by an import.
            current.email = row.email.strip().lower()
        elif current.email and row.email and current.email.lower() != row.email.strip().lower():
            if row.conflict_resolution != "skip": raise HTTPException(409,"Every conflicting email requires explicit skip resolution")
            skipped += 1
        elif current.full_name != row.full_name.strip():
            if row.conflict_resolution != "skip": raise HTTPException(409,"Every conflicting name requires explicit skip resolution")
            skipped += 1
    record_audit_event(
        db,
        actor_admin_id=admin.id,
        event_type="STUDENT_IMPORT_COMMITTED",
        entity_type="student_import",
        entity_id=admin.id,
        payload={"created": created, "skipped_conflicts": skipped, "reviewed_rows": len(payload.rows)},
    )
    db.commit(); return {"created":created,"skipped_conflicts":skipped}
