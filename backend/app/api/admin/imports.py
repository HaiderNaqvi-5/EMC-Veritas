from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.admin.students import require_admin
from app.db.session import get_db
from app.models.domain import Student
from app.schemas.operations import ImportCommit, StudentCreate
from app.services.audit import record_audit_event
from app.services.imports import participant_export, preview_students
from app.services.students import create_student, normalize_roll_number

router=APIRouter(prefix="/imports",tags=["admin-imports"])
@router.post("/students/preview")
async def preview(file: UploadFile=File(...), _: UUID=Depends(require_admin), db: Session=Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".xlsx"): raise HTTPException(400,"Only .xlsx files are accepted")
    try: return preview_students(db, await file.read())
    except ValueError as error: raise HTTPException(400,str(error))

@router.get("/activities/{activity_id}/participants/export")
def export(activity_id: UUID, _: UUID=Depends(require_admin), db: Session=Depends(get_db)):
    try: content=participant_export(db,activity_id)
    except LookupError: raise HTTPException(404,"Activity not found")
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition":"attachment; filename=Export Participants.xlsx"})

@router.post("/students/commit")
def commit(payload: ImportCommit, admin_id: UUID=Depends(require_admin), db: Session=Depends(get_db)):
    created=0; skipped=0
    for row in payload.rows:
        canonical_roll_number = normalize_roll_number(row.roll_number)
        current=db.query(Student).filter(Student.roll_number == canonical_roll_number).one_or_none()
        if current is None:
            create_student(
                db,
                StudentCreate(roll_number=canonical_roll_number, full_name=row.full_name.strip()),
            )
            created += 1
        elif current.full_name != row.full_name.strip():
            if row.conflict_resolution != "skip": raise HTTPException(409,"Every conflicting name requires explicit skip resolution")
            skipped += 1
    record_audit_event(
        db,
        actor_admin_id=admin_id,
        event_type="STUDENT_IMPORT_COMMITTED",
        entity_type="student_import",
        entity_id=admin_id,
        payload={"created": created, "skipped_conflicts": skipped, "reviewed_rows": len(payload.rows)},
    )
    db.commit(); return {"created":created,"skipped_conflicts":skipped}
