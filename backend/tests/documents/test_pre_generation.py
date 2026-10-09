from types import SimpleNamespace
from uuid import uuid4

from app.api.admin import documents
from app.models.domain import DocumentType
from app.schemas.documents import ActivityPreGenerationResponse


def test_ec_pre_generation_uses_ec_renderer_and_document_type(monkeypatch) -> None:
    activity_id = uuid4()
    db = object()
    admin = SimpleNamespace(id=uuid4())
    captured: dict[str, object] = {}
    expected = ActivityPreGenerationResponse(
        activity_id=activity_id,
        total_documents=2,
        ready_documents=2,
        generated_documents=1,
        remaining_documents=0,
        failed_document_ids=[],
    )

    def prepare(selected_activity_id, **kwargs):
        captured["activity_id"] = selected_activity_id
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(documents, "_pre_generate_activity_document_batch", prepare)

    result = documents.pre_generate_ec_documents(
        activity_id,
        limit=7,
        db=db,
        admin=admin,
    )

    assert result == expected
    assert captured == {
        "activity_id": activity_id,
        "document_type": DocumentType.EXECUTIVE_COUNCIL_CERTIFICATE,
        "rendering_profile": "executive_council",
        "audit_event_type": "ACTIVITY_EC_DOCUMENTS_PREGENERATED",
        "limit": 7,
        "db": db,
        "admin": admin,
    }
