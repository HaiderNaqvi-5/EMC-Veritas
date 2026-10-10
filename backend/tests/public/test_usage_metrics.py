from sqlalchemy.dialects import postgresql

from app.services.public_usage import record_public_usage, student_fingerprint


class _Db:
    def __init__(self) -> None:
        self.statement = None

    def execute(self, statement: object) -> None:
        self.statement = statement


def test_student_fingerprint_is_stable_and_does_not_retain_roll_number() -> None:
    fingerprint = student_fingerprint("FA21-BCS-001")

    assert fingerprint == student_fingerprint("FA21-BCS-001")
    assert len(fingerprint) == 64
    assert "FA21-BCS-001" not in fingerprint


def test_record_public_usage_uses_an_atomic_upsert() -> None:
    db = _Db()

    record_public_usage(db, roll_number="FA21-BCS-001", event="download")

    compiled = db.statement.compile(dialect=postgresql.dialect())
    assert "ON CONFLICT (student_fingerprint) DO UPDATE" in str(compiled)
    assert "FA21-BCS-001" not in repr(compiled.params)
