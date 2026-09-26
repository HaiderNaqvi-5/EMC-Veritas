import asyncio
import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-only-key")
os.environ.setdefault("SESSION_SECRET", "test-only-session-secret")

import httpx

from app.main import app


def test_readiness_endpoint() -> None:
    async def request_readiness() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/api/health/ready")

    response = asyncio.run(request_readiness())
    assert response.status_code == 200
    assert response.json() == {"ready": True}


def test_build_revision_endpoint_reports_the_render_revision() -> None:
    previous_revision = os.environ.get("RENDER_GIT_COMMIT")
    os.environ["RENDER_GIT_COMMIT"] = "74d1071-test"
    try:
        async def request_build_revision() -> httpx.Response:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get("/api/health/build")

        response = asyncio.run(request_build_revision())
        assert response.status_code == 200
        assert response.json() == {"revision": "74d1071-test"}
    finally:
        if previous_revision is None:
            os.environ.pop("RENDER_GIT_COMMIT", None)
        else:
            os.environ["RENDER_GIT_COMMIT"] = previous_revision
