from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models.domain import DocumentStatus


class _Rows:
    def __init__(self, value: object) -> None:
        self.value = value

    def first(self) -> object:
        return self.value


class _Scalars:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def all(self) -> list[object]:
        return self.values


class _Db:
    def __init__(self, row: tuple[object, object, object], template: object, fields: list[object]) -> None:
        self.row = row
        self.template = template
        self.fields = fields
        self.committed = False

    def execute(self, query: object) -> _Rows:
        return _Rows(self.row)

    def scalar(self, query: object) -> object:
        return self.template

    def scalars(self, query: object) -> _Scalars:
        return _Scalars(self.fields)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        raise AssertionError("A valid download should not roll back")


def test_public_download_uses_approved_template_and_commits_cache(monkeypatch) -> None:
    document_id = uuid4()
    document = SimpleNamespace(
        id=document_id,
        verification_id="EMC-VALID123",
        status=DocumentStatus.VALID,
        issue_date=date(2026, 9, 23),
    )
    student = SimpleNamespace(full_name="Ayesha Khan", roll_number="FA21-BCS-001")
    activity = SimpleNamespace(id=uuid4(), template_id=uuid4(), name="Welcome Week", activity_date=date(2026, 9, 1))
    template = SimpleNamespace(id=activity.template_id, storage_key="templates/welcome.pdf")
    fields = [SimpleNamespace(field_name="student_name")]
    db = _Db((document, student, activity), template, fields)

    class Storage:
        def download(self, key: str) -> bytes:
            assert key == "templates/welcome.pdf"
            return b"template"

    captured: dict[str, object] = {}

    def generate(db_argument: object, **kwargs: object) -> bytes:
        assert db_argument is db
        captured.update(kwargs)
        return b"%PDF-test-document"

    import app.api.public.router as public_router

    monkeypatch.setattr(public_router, "SupabaseStorage", Storage)
    monkeypatch.setattr(public_router, "generate_on_first_download", generate)
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = TestClient(app).get(f"/api/public/documents/{document_id}/download")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.content == b"%PDF-test-document"
    assert response.headers["content-type"] == "application/pdf"
    assert "EMC-EMC-VALID123.pdf" in response.headers["content-disposition"]
    assert db.committed is True
    assert captured["template_fields"] == fields
    assert captured["values"] == {
        "student_name": "Ayesha Khan",
        "roll_number": "FA21-BCS-001",
        "activity_name": "Welcome Week",
        "activity_date": date(2026, 9, 1),
        "issue_date": date(2026, 9, 23),
        "verification_id": "EMC-VALID123",
    }


def test_public_download_rejects_revoked_document(monkeypatch) -> None:
    document = SimpleNamespace(id=uuid4(), verification_id="EMC-REVOKED", status=DocumentStatus.REVOKED)
    db = _Db((document, object(), object()), object(), [])
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = TestClient(app).get(f"/api/public/documents/{document.id}/download")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 410
