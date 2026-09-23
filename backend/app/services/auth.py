from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import Admin, Student

hasher = PasswordHasher()


def find_admin_by_roll_number(db: Session, roll_number: str) -> Admin | None:
    return db.scalar(select(Admin).join(Student, Admin.student_id == Student.id).where(Student.roll_number == roll_number.strip()))


def authenticate(db: Session, roll_number: str, password: str) -> Admin | None:
    admin = find_admin_by_roll_number(db, roll_number)
    if admin is None or not admin.active:
        return None
    try:
        hasher.verify(admin.password_hash, password)
    except VerifyMismatchError:
        return None
    return admin


def change_password(admin: Admin, current_password: str, new_password: str) -> bool:
    try:
        hasher.verify(admin.password_hash, current_password)
    except VerifyMismatchError:
        return False
    admin.password_hash = hasher.hash(new_password)
    admin.must_change_password = False
    return True
