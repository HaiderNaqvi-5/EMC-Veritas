from types import SimpleNamespace
from uuid import uuid4

import pytest
from starlette.requests import Request

from app.api.admin.dependencies import current_active_admin, super_admin_required
from app.models.domain import AdminRole


class _Db:
    def __init__(self, admin: object | None) -> None:
        self.admin = admin

    def get(self, model: object, identifier: object) -> object | None:
        return self.admin


def _request(session: dict[str, str]) -> Request:
    request = Request({"type": "http", "headers": []})
    request.scope["session"] = session
    return request


def test_current_active_admin_rejects_missing_session() -> None:
    with pytest.raises(Exception) as error:
        current_active_admin(_request({}), _Db(None))
    assert error.value.status_code == 401


def test_super_admin_guard_requires_super_admin_role() -> None:
    admin = SimpleNamespace(id=uuid4(), active=True, role=AdminRole.ADMIN)
    with pytest.raises(Exception) as error:
        super_admin_required(admin)
    assert error.value.status_code == 403


def test_current_active_admin_accepts_active_session() -> None:
    admin = SimpleNamespace(id=uuid4(), active=True, role=AdminRole.SUPER_ADMIN)
    assert current_active_admin(_request({"admin_id": str(admin.id)}), _Db(admin)) is admin
