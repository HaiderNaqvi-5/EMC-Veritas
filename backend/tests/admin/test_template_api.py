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


def test_template_listing_requires_authenticated_super_admin() -> None:
    response = TestClient(app).get("/api/admin/templates")
    assert response.status_code == 401
    assert response.json() == {"detail": "Admin session required"}


def test_template_source_requires_authenticated_super_admin() -> None:
    response = TestClient(app).get("/api/admin/templates/00000000-0000-0000-0000-000000000000/source")
    assert response.status_code == 401
    assert response.json() == {"detail": "Admin session required"}


def test_template_page_image_requires_authenticated_super_admin() -> None:
    response = TestClient(app).get("/api/admin/templates/00000000-0000-0000-0000-000000000000/pages/1")
    assert response.status_code == 401
    assert response.json() == {"detail": "Admin session required"}


def test_leadership_template_workflow_requires_authenticated_super_admin() -> None:
    response = TestClient(app).post(
        "/api/admin/leadership-templates/upload",
        data={
            "name": "President recognition",
            "role": "President",
            "document_type": "LEADERSHIP_RECOGNITION",
        },
        files={"file": ("letter.pdf", b"%PDF-1.4", "application/pdf")},
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


def test_activity_issue_requires_authenticated_admin() -> None:
    response = TestClient(app).post(
        "/api/admin/documents/activities/00000000-0000-0000-0000-000000000000/issue"
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Admin session required"}


def test_admin_document_listing_requires_authenticated_admin() -> None:
    response = TestClient(app).get("/api/admin/documents")
    assert response.status_code == 401
    assert response.json() == {"detail": "Admin session required"}


def test_executive_membership_listing_requires_authenticated_admin() -> None:
    response = TestClient(app).get("/api/admin/executive-memberships")
    assert response.status_code == 401
    assert response.json() == {"detail": "Admin session required"}


def test_signatory_management_requires_authenticated_admin() -> None:
    response = TestClient(app).post(
        "/api/admin/signatories",
        data={
            "name": "Dr. Example",
            "official_title": "DSA",
            "effective_start_date": "2026-01-01",
        },
        files={"signature": ("signature.png", b"png", "image/png")},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Admin session required"}


def test_document_revocation_requires_authenticated_admin() -> None:
    response = TestClient(app).post(
        "/api/admin/documents/00000000-0000-0000-0000-000000000000/revoke"
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Admin session required"}


def test_document_reissue_requires_authenticated_admin() -> None:
    response = TestClient(app).post(
        "/api/admin/documents/00000000-0000-0000-0000-000000000000/reissue"
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Admin session required"}


def test_audit_log_requires_authenticated_super_admin() -> None:
    response = TestClient(app).get("/api/admin/audit")
    assert response.status_code == 401
    assert response.json() == {"detail": "Admin session required"}


def test_template_preview_requires_authenticated_admin() -> None:
    response = TestClient(app).post(
        "/api/admin/templates/00000000-0000-0000-0000-000000000000/preview",
        json={
            "student_id": "00000000-0000-0000-0000-000000000000",
            "activity_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Admin session required"}
