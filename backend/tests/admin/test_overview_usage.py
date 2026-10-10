from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.admin.dependencies import current_active_admin
from app.db.session import get_db
from app.main import app


class _Result:
    def one(self) -> tuple[int, int, int, int, datetime]:
        return (18, 42, 11, 27, datetime(2026, 10, 11, tzinfo=UTC))


class _Db:
    def execute(self, query: object) -> _Result:
        return _Result()


def test_admin_overview_returns_aggregate_usage_only() -> None:
    app.dependency_overrides[get_db] = lambda: _Db()
    app.dependency_overrides[current_active_admin] = lambda: SimpleNamespace(id="admin")
    try:
        response = TestClient(app).get("/api/admin/overview/public-usage")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "unique_record_viewers": 18,
        "total_record_lookups": 42,
        "unique_downloaders": 11,
        "total_downloads": 27,
        "tracking_started_at": "2026-10-11T00:00:00Z",
    }
    assert "student" not in response.text.lower()
