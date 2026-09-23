import json
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.api.admin.documents import _reissue_leadership_document
from app.models.domain import DocumentStatus, DocumentType


class _Scalars:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def all(self) -> list[object]:
        return self.values


class _Db:
    def __init__(self, signatories: list[object]) -> None:
        self.signatories = signatories
        self.committed = False

    def scalars(self, query: object) -> _Scalars:
        return _Scalars(self.signatories)

    def commit(self) -> None:
        self.committed = True


def test_leadership_reissue_keeps_reserved_context_and_supersedes_original(monkeypatch) -> None:
    membership_id = uuid4()
    template_id = uuid4()
    document = SimpleNamespace(
        id=uuid4(),
        student_id=uuid4(),
        executive_membership_id=membership_id,
        leadership_template_id=template_id,
        document_type=DocumentType.LEADERSHIP_RECOGNITION,
        render_payload_json=json.dumps({"student_name": "Ayesha Khan", "issue_date": "2026-08-31"}),
        status=DocumentStatus.VALID,
        version=1,
    )
    admin = SimpleNamespace(id=uuid4())
    signatory = SimpleNamespace(id=uuid4(), official_title="DSA")
    db = _Db([signatory])
    reserved: dict[str, object] = {}

    def reserve(db_argument: object, **kwargs: object) -> object:
        assert db_argument is db
        reserved.update(kwargs)
        return SimpleNamespace(id=uuid4(), version=2)

    from app.api.admin import documents

    monkeypatch.setattr(documents, "reserve_document", reserve)
    monkeypatch.setattr(documents, "record_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(documents, "EMC_TIMEZONE", ZoneInfo("UTC"))

    result = _reissue_leadership_document(db, document, admin)

    assert document.status is DocumentStatus.SUPERSEDED
    assert reserved["executive_membership_id"] == membership_id
    assert reserved["leadership_template_id"] == template_id
    assert reserved["signatories"] == (signatory,)
    assert reserved["version"] == 2
    assert reserved["render_values"]["student_name"] == "Ayesha Khan"
    assert result.version == 2
    assert db.committed is True
