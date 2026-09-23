import asyncio

import httpx

from app.main import app


async def request(method: str, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path)


def test_document_discovery_requires_an_admin_session() -> None:
    response = asyncio.run(request("GET", "/api/admin/documents"))
    assert response.status_code == 401
    assert response.json() == {"detail": "Admin session required"}


def test_executive_membership_discovery_requires_an_admin_session() -> None:
    response = asyncio.run(request("GET", "/api/admin/executive-memberships"))
    assert response.status_code == 401
    assert response.json() == {"detail": "Admin session required"}
