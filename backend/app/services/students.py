from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.domain import (
    ActivityParticipant,
    Admin,
    ExecutiveMembership,
    IssuedDocument,
    Student,
)
from app.schemas.operations import StudentCreate


def normalize_roll_number(roll_number: str) -> str:
    """Use one canonical identity form while allowing case-insensitive entry."""
    return roll_number.strip().upper()


def list_students(db: Session) -> list[Student]:
    return list(db.scalars(select(Student).order_by(Student.full_name, Student.roll_number)))


def create_student(db: Session, payload: StudentCreate) -> Student:
    roll_number = normalize_roll_number(payload.roll_number)
    student = db.scalar(select(Student).where(Student.roll_number == roll_number))
    if student is not None:
        if student.active:
            raise ValueError("A student with this roll number already exists")
        # A roll number represents the student's identity.  Keep historical
        # document links intact, but make a deactivated record usable again.
        student.full_name = payload.full_name.strip()
        student.active = True
        db.flush()
        return student
    student = Student(roll_number=roll_number, full_name=payload.full_name.strip(), active=True)
    db.add(student)
    db.flush()
    return student


def deactivate_student(db: Session, student: Student) -> Student:
    student.active = False
    db.flush()
    return student


def delete_inactive_student(db: Session, student: Student) -> None:
    """Remove a disposable inactive student without ever breaking issued history."""
    if student.active:
        raise ValueError("Deactivate this student before deleting the record")
    if db.scalar(select(IssuedDocument.id).where(IssuedDocument.student_id == student.id)):
        raise ValueError("Students with issued documents cannot be deleted; keep them deactivated")
    db.execute(delete(ActivityParticipant).where(ActivityParticipant.student_id == student.id))
    db.execute(delete(ExecutiveMembership).where(ExecutiveMembership.student_id == student.id))
    db.execute(delete(Admin).where(Admin.student_id == student.id))
    db.delete(student)
    db.flush()
