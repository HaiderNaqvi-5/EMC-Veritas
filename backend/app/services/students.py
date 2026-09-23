from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import Student
from app.schemas.operations import StudentCreate


def list_students(db: Session) -> list[Student]:
    return list(db.scalars(select(Student).order_by(Student.full_name, Student.roll_number)))


def create_student(db: Session, payload: StudentCreate) -> Student:
    student = Student(roll_number=payload.roll_number.strip(), full_name=payload.full_name.strip(), active=True)
    db.add(student)
    db.flush()
    return student


def deactivate_student(db: Session, student: Student) -> Student:
    student.active = False
    db.flush()
    return student
