from datetime import UTC, datetime, timedelta
from uuid import uuid4

from argon2 import PasswordHasher

from app.models.domain import Student, StudentAccountToken, StudentAccountTokenPurpose
from app.services.student_accounts import activate_account, consume_token, issue_token, mask_email


class TokenDatabase:
    def __init__(self, token=None, student=None):
        self.added = []
        self.token = token
        self.student = student

    def add(self, item):
        self.added.append(item)

    def scalar(self, _query):
        return self.token

    def get(self, _model, _id):
        return self.student


def student() -> Student:
    return Student(id=uuid4(), roll_number="22-CS-1", full_name="Ahmed Khan", email="ahmed.khan@example.edu", active=True)


def test_activation_token_is_random_and_only_hash_is_persisted():
    db = TokenDatabase(); record = student()
    raw = issue_token(db, record, StudentAccountTokenPurpose.ACTIVATION)
    saved = db.added[0]
    assert raw != saved.token_hash
    assert len(saved.token_hash) == 64
    assert saved.student_id == record.id
    assert saved.expires_at > datetime.now(UTC)


def test_expired_or_consumed_token_cannot_activate_account():
    record = student()
    expired = StudentAccountToken(student_id=record.id, purpose=StudentAccountTokenPurpose.ACTIVATION, token_hash="a" * 64, expires_at=datetime.now(UTC) - timedelta(seconds=1))
    assert consume_token(TokenDatabase(expired, record), "any-token", StudentAccountTokenPurpose.ACTIVATION) is None


def test_activation_hashes_password_and_marks_student_email_verified():
    record = student(); db = TokenDatabase()
    account = activate_account(db, record, "correct-horse-battery-staple")
    assert account.password_hash != "correct-horse-battery-staple"
    assert PasswordHasher().verify(account.password_hash, "correct-horse-battery-staple") is True
    assert record.email_verified_at is not None


def test_email_hint_is_masked():
    assert mask_email("ahmed.khan@example.edu") == "a•••••••••@example.edu"
    assert mask_email(None) is None
