from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.domain import Student
from app.schemas.operations import StudentCreate, StudentResponse
from app.services.audit import record_audit_event
from app.services.students import create_student, deactivate_student, list_students

router = APIRouter(prefix="/students", tags=["admin-students"])


def require_admin(request: Request) -> UUID:
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin session required")
    return UUID(admin_id)


@router.get("", response_model=list[StudentResponse])
def get_students(_: UUID = Depends(require_admin), db: Session = Depends(get_db)) -> list[Student]:
    return list_students(db)


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def add_student(payload: StudentCreate, admin_id: UUID = Depends(require_admin), db: Session = Depends(get_db)) -> Student:
    try:
        student = create_student(db, payload)
        record_audit_event(db, event_type="STUDENT_CREATED", entity_type="student", entity_id=student.id, payload={"roll_number": student.roll_number}, actor_admin_id=admin_id)
        db.commit(); db.refresh(student)
        return student
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A student with this roll number already exists")


@router.post("/{student_id}/deactivate", response_model=StudentResponse)
def deactivate(student_id: str, admin_id: UUID = Depends(require_admin), db: Session = Depends(get_db)) -> Student:
    student = db.get(Student, student_id)
    if student is None: raise HTTPException(status_code=404, detail="Student not found")
    deactivate_student(db, student)
    record_audit_event(db, event_type="STUDENT_DEACTIVATED", entity_type="student", entity_id=student.id, payload={}, actor_admin_id=admin_id)
    db.commit(); db.refresh(student)
    return student
