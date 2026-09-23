from uuid import uuid4

from argon2 import PasswordHasher

from app.models.domain import Admin, AdminRole
from app.services.auth import authenticate, change_password


class FakeDatabase:
    def __init__(self, admin: Admin | None) -> None:
        self.admin = admin

    def scalar(self, _query) -> Admin | None:
        return self.admin


def make_admin() -> Admin:
    return Admin(id=uuid4(), student_id=uuid4(), password_hash=PasswordHasher().hash("temporary-password"), role=AdminRole.ADMIN, active=True, must_change_password=True)


def test_authenticate_accepts_valid_active_admin() -> None:
    admin = make_admin()
    assert authenticate(FakeDatabase(admin), "22-CS-1", "temporary-password") is admin


def test_authenticate_rejects_invalid_password_or_inactive_admin() -> None:
    admin = make_admin()
    assert authenticate(FakeDatabase(admin), "22-CS-1", "wrong-password") is None
    admin.active = False
    assert authenticate(FakeDatabase(admin), "22-CS-1", "temporary-password") is None


def test_change_password_clears_temporary_requirement() -> None:
    admin = make_admin()
    assert change_password(admin, "temporary-password", "a-safe-new-password") is True
    assert admin.must_change_password is False
    assert PasswordHasher().verify(admin.password_hash, "a-safe-new-password") is True
