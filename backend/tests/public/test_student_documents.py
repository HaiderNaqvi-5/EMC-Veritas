from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models.domain import DocumentStatus, DocumentType


class _Db:
    """Fake DB: scalar() returns the student; execute(...).all() returns document rows."""

    def __init__(self, student: object | None, rows: list) -> None:
        self.student = student
        self.rows = rows

    def scalar(self, query: object) -> object | None:
        return self.student

    def execute(self, query: object) -> object:
        rows = self.rows

        class _Result:
            def all(self) -> list:
                return rows

        return _Result()


def _student() -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), full_name="Ayesha Khan", roll_number="FA21-BCS-001")


def _document(document_type: DocumentType) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        document_type=document_type,
        status=DocumentStatus.VALID,
        issue_date=date(2026, 9, 23),
    )


def _get(roll_number: str, student: object | None, rows: list):
    app.dependency_overrides[get_db] = lambda: _Db(student, rows)
    try:
        client = TestClient(app)
        return client.get(f"/api/public/students/{roll_number}/documents")
    finally:
        app.dependency_overrides.clear()


def test_student_documents_splits_certificate_types() -> None:
    rows = [
        (_document(DocumentType.ACTIVITY_CERTIFICATE), "Welcome Week", date(2026, 9, 1)),
        (_document(DocumentType.LEADERSHIP_RECOGNITION), None, None),
    ]
    response = _get("FA21-BCS-001", _student(), rows)

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Ayesha Khan"
    assert body["roll_number"] == "FA21-BCS-001"
    assert len(body["activity_certificates"]) == 1
    assert body["activity_certificates"][0]["title"] == "Welcome Week"
    assert body["activity_certificates"][0]["status"] == "VALID"
    assert len(body["leadership_recognition"]) == 1
    # Falls back to the document type label when there is no activity.
    assert body["leadership_recognition"][0]["title"] == "Leadership Recognition"


def test_student_documents_returns_404_for_unknown_roll_number() -> None:
    response = _get("FA21-BCS-999", None, [])
    assert response.status_code == 404


def test_student_documents_returns_empty_lists_when_no_documents() -> None:
    response = _get("fa21-bcs-001", _student(), [])

    assert response.status_code == 200
    body = response.json()
    assert body["activity_certificates"] == []
    assert body["leadership_recognition"] == []
