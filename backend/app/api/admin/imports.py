from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.admin.students import require_admin
from app.db.session import get_db
from app.models.domain import Student
from app.schemas.operations import ImportCommit
from app.services.imports import participant_export, preview_students

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
def commit(payload: ImportCommit, _: UUID=Depends(require_admin), db: Session=Depends(get_db)):
    created=0; skipped=0
    for row in payload.rows:
        current=db.query(Student).filter(Student.roll_number == row.roll_number.strip()).one_or_none()
        if current is None: db.add(Student(roll_number=row.roll_number.strip(),full_name=row.full_name.strip(),active=True)); created += 1
        elif current.full_name != row.full_name.strip():
            if row.conflict_resolution != "skip": raise HTTPException(409,"Every conflicting name requires explicit skip resolution")
            skipped += 1
    db.commit(); return {"created":created,"skipped_conflicts":skipped}
