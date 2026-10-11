from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


class _Db:
    def __init__(self, duplicate: object | None = None) -> None:
        self.duplicate = duplicate
        self.added = None
        self.committed = False

    def scalar(self, statement: object) -> object | None:
        return self.duplicate

    def add(self, item: object) -> None:
        self.added = item

    def commit(self) -> None:
        self.committed = True


def _payload() -> dict[str, str]:
    return {
        "roll_number": "2k22-bscs-238",
        "full_name": "Student Name",
        "contact_email": "STUDENT@example.com",
        "problem_category": "MISSING_CERTIFICATE",
        "problem_details": "My issued activity certificate is not visible.",
    }


def test_public_support_request_is_normalized_and_created() -> None:
    db = _Db()
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = TestClient(app).post("/api/public/support-requests", json=_payload())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["ticket_number"].startswith("EMC-HELP-")
    assert db.added.roll_number == "2K22-BSCS-238"
    assert db.added.contact_email == "student@example.com"
    assert db.committed is True


def test_public_support_request_reuses_active_ticket_guard() -> None:
    db = _Db(SimpleNamespace(ticket_number="EMC-HELP-EXISTING"))
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = TestClient(app).post("/api/public/support-requests", json=_payload())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert "EMC-HELP-EXISTING" in response.json()["detail"]
    assert db.added is None
