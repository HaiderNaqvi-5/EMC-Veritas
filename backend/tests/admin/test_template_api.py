from fastapi.testclient import TestClient

from app.main import app


def test_template_upload_requires_authenticated_super_admin() -> None:
    response = TestClient(app).post(
        "/api/admin/templates/upload",
        data={"name": "Activity certificate"},
        files={"file": ("certificate.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Admin session required"}


def test_template_configuration_requires_authenticated_super_admin() -> None:
    response = TestClient(app).post(
        "/api/admin/templates/00000000-0000-0000-0000-000000000000/fields",
        json={"fields": [{"field_name": "student_name", "page_number": 1, "x": 10, "y": 10, "width": 100, "height": 20}]},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Admin session required"}
