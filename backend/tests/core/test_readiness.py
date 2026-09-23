import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-only-key")

from fastapi.testclient import TestClient

from app.main import app


def test_readiness_endpoint() -> None:
    response = TestClient(app).get("/api/health/ready")
    assert response.status_code == 200
    assert response.json() == {"ready": True}
