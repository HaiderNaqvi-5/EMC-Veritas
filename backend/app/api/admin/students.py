from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.admin.dependencies import current_active_admin
from app.db.session import get_db
from app.models.domain import Admin, Student
from app.schemas.operations import StudentCreate, StudentResponse, StudentUpdate
from app.services.audit import record_audit_event
from app.services.students import (
    create_student,
    deactivate_student,
    delete_inactive_student,
    list_students,
    update_student,
)

router = APIRouter(prefix="/students", tags=["admin-students"])


@router.get("", response_model=list[StudentResponse])
def get_students(_: Admin = Depends(current_active_admin), db: Session = Depends(get_db)) -> list[Student]:
    return list_students(db)


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def add_student(payload: StudentCreate, admin: Admin = Depends(current_active_admin), db: Session = Depends(get_db)) -> Student:
    try:
        student = create_student(db, payload)
        record_audit_event(db, event_type="STUDENT_CREATED", entity_type="student", entity_id=student.id, payload={"roll_number": student.roll_number}, actor_admin_id=admin.id)
        db.commit(); db.refresh(student)
        return student
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A student with this roll number already exists")
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.put("/{student_id}", response_model=StudentResponse)
def edit_student(
    student_id: str,
    payload: StudentUpdate,
    admin: Admin = Depends(current_active_admin),
    db: Session = Depends(get_db),
) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    before = {"roll_number": student.roll_number, "full_name": student.full_name}
    try:
        update_student(db, student, payload)
        record_audit_event(
            db,
            event_type="STUDENT_IDENTITY_UPDATED",
            entity_type="student",
            entity_id=student.id,
            payload={
                "before": before,
                "after": {"roll_number": student.roll_number, "full_name": student.full_name},
            },
            actor_admin_id=admin.id,
        )
        db.commit()
        db.refresh(student)
        return student
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A student with this roll number already exists",
        )
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post("/{student_id}/deactivate", response_model=StudentResponse)
def deactivate(student_id: str, admin: Admin = Depends(current_active_admin), db: Session = Depends(get_db)) -> Student:
    student = db.get(Student, student_id)
    if student is None: raise HTTPException(status_code=404, detail="Student not found")
    deactivate_student(db, student)
    record_audit_event(db, event_type="STUDENT_DEACTIVATED", entity_type="student", entity_id=student.id, payload={}, actor_admin_id=admin.id)
    db.commit(); db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: str, admin: Admin = Depends(current_active_admin), db: Session = Depends(get_db)) -> None:
    student = db.get(Student, student_id)
    if student is None:
        # A browser retry after a dropped response must be safe: the first
        # request may have completed even though the UI did not receive 204.
        return
    roll_number = student.roll_number
    try:
        delete_inactive_student(db, student, protected_admin_id=admin.id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    record_audit_event(db, event_type="STUDENT_DELETED", entity_type="student", entity_id=student_id, payload={"roll_number": roll_number}, actor_admin_id=admin.id)
    db.commit()
