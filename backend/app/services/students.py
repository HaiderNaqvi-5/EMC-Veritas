from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models.domain import (
    ActivityParticipant,
    Admin,
    AuditLog,
    DocumentSignatory,
    DocumentStatus,
    ExecutiveMembership,
    IssuedDocument,
    Student,
)
from app.schemas.operations import StudentCreate, StudentUpdate


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
        if payload.email:
            student.email = payload.email.strip().lower()
        student.active = True
        db.flush()
        return student
    student = Student(
        roll_number=roll_number,
        full_name=payload.full_name.strip(),
        email=payload.email.strip().lower() if payload.email else None,
        active=True,
    )
    db.add(student)
    db.flush()
    return student


def update_student(db: Session, student: Student, payload: StudentUpdate) -> Student:
    """Correct a student's mutable identity fields without replacing its ID."""
    roll_number = normalize_roll_number(payload.roll_number)
    full_name = payload.full_name.strip()
    if not full_name:
        raise ValueError("Student name cannot be blank")
    conflicting_student = db.scalar(
        select(Student).where(Student.roll_number == roll_number, Student.id != student.id)
    )
    if conflicting_student is not None:
        raise ValueError("A student with this roll number already exists")
    student.roll_number = roll_number
    student.full_name = full_name
    db.flush()
    return student


def deactivate_student(db: Session, student: Student) -> Student:
    student.active = False
    db.flush()
    return student


def delete_inactive_student(
    db: Session, student: Student, *, protected_admin_id: UUID | None = None
) -> None:
    """Remove a disposable inactive student without ever breaking issued history."""
    if student.active:
        raise ValueError("Deactivate this student before deleting the record")
    if db.scalar(
        select(IssuedDocument.id).where(
            IssuedDocument.student_id == student.id,
            IssuedDocument.status != DocumentStatus.REVOKED,
        )
    ):
        raise ValueError("Students with active or superseded documents cannot be deleted; revoke them first")
    linked_admin_ids = list(db.scalars(select(Admin.id).where(Admin.student_id == student.id)))
    if protected_admin_id in linked_admin_ids:
        raise ValueError("You cannot delete the student record for your own administrator account")
    db.execute(delete(ActivityParticipant).where(ActivityParticipant.student_id == student.id))
    db.execute(delete(ExecutiveMembership).where(ExecutiveMembership.student_id == student.id))
    revoked_document_ids = select(IssuedDocument.id).where(
        IssuedDocument.student_id == student.id,
        IssuedDocument.status == DocumentStatus.REVOKED,
    )
    # A revoked document is no longer a public record. Delete its immutable
    # signatory snapshots first, then the revoked document rows, so a test
    # student can be fully removed without violating foreign-key constraints.
    db.execute(delete(DocumentSignatory).where(DocumentSignatory.issued_document_id.in_(revoked_document_ids)))
    db.execute(
        delete(IssuedDocument).where(
            IssuedDocument.student_id == student.id,
            IssuedDocument.status == DocumentStatus.REVOKED,
        )
    )
    # Audit history must survive deletion of a disposable administrator account.
    # Preserve the event while clearing only its now-invalid actor foreign key.
    if linked_admin_ids:
        db.execute(update(AuditLog).where(AuditLog.actor_admin_id.in_(linked_admin_ids)).values(actor_admin_id=None))
    db.execute(delete(Admin).where(Admin.student_id == student.id))
    db.delete(student)
    db.flush()
