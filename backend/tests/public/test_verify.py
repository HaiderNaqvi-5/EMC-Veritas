from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models.domain import DocumentStatus, DocumentType


class _Db:
    """Fake DB: execute(...).first() returns the verify join row (or None)."""

    def __init__(self, row: object | None) -> None:
        self.row = row

    def execute(self, query: object) -> object:
        row = self.row

        class _Result:
            def first(self) -> object | None:
                return row

        return _Result()


def _document(status: DocumentStatus = DocumentStatus.VALID) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        verification_id="EMC-VALID123",
        status=status,
        document_type=DocumentType.ACTIVITY_CERTIFICATE,
        issue_date=date(2026, 9, 23),
    )


def _get(verification_id: str, row: object | None):
    app.dependency_overrides[get_db] = lambda: _Db(row)
    try:
        return TestClient(app).get(f"/api/public/verify/{verification_id}")
    finally:
        app.dependency_overrides.clear()


def test_verify_returns_record_for_valid_document() -> None:
    student = SimpleNamespace(full_name="Ayesha Khan", roll_number="FA21-BCS-001")
    response = _get("EMC-VALID123", (_document(), student, "Welcome Week", date(2026, 9, 1)))

    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is True
    assert body["status"] == "VALID"
    assert body["verification_id"] == "EMC-VALID123"
    assert body["full_name"] == "Ayesha Khan"
    assert body["roll_number"] == "FA21-BCS-001"
    assert body["document_type"] == "ACTIVITY_CERTIFICATE"
    assert body["context"] == "Welcome Week"
    assert body["issue_date"] == "2026-09-23"


def test_verify_returns_404_for_unknown_id() -> None:
    response = _get("EMC-NOPE1234", None)
    assert response.status_code == 404


def test_verify_reports_revoked_document_as_not_verified() -> None:
    # Revocation must resolve (not 404) so verifiers see the true status.
    student = SimpleNamespace(full_name="Ayesha Khan", roll_number="FA21-BCS-001")
    response = _get("EMC-VALID123", (_document(DocumentStatus.REVOKED), student, "Welcome Week", date(2026, 9, 1)))

    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is False
    assert body["status"] == "REVOKED"
