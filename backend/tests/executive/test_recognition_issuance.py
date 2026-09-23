from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.models.domain import DocumentType, MembershipStatus
from app.services.executive.issuance import _preflight_session_recognition
from app.services.executive.letters import REQUIRED_LEADERSHIP_TEMPLATE_FIELDS


class _Scalars:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def all(self) -> list[object]:
        return self.values


class _Rows:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def all(self) -> list[object]:
        return self.values


class _RecognitionDb:
    def __init__(self, *, scalar_values: list[object], scalar_lists: list[list[object]], rows: list[object]) -> None:
        self.scalar_values = scalar_values
        self.scalar_lists = scalar_lists
        self.rows = rows

    def execute(self, query: object) -> _Rows:
        return _Rows(self.rows)

    def scalar(self, query: object) -> object:
        return self.scalar_values.pop(0)

    def scalars(self, query: object) -> _Scalars:
        return _Scalars(self.scalar_lists.pop(0))


def _field(name: str) -> object:
    return SimpleNamespace(field_name=name)


def test_session_recognition_preflight_reserves_two_fixed_template_plans() -> None:
    session = SimpleNamespace(id=uuid4(), name="2025-26", end_date=date(2026, 8, 31))
    membership = SimpleNamespace(
        id=uuid4(),
        student_id=uuid4(),
        role="President",
        start_date=date(2025, 9, 1),
        end_date=date(2026, 8, 31),
        status=MembershipStatus.COMPLETED,
    )
    student = SimpleNamespace(full_name="Ayesha Khan", roll_number="FA21-BCS-001")
    dsa = SimpleNamespace(
        id=uuid4(), official_title="DSA", active=True,
        effective_start_date=date(2025, 1, 1), effective_end_date=None,
    )
    hod = SimpleNamespace(
        id=uuid4(), official_title="HOD", active=True,
        effective_start_date=date(2025, 1, 1), effective_end_date=None,
    )
    recognition = SimpleNamespace(
        id=uuid4(), role="President", document_type=DocumentType.LEADERSHIP_RECOGNITION,
        signature_handling="retain", active=True, archived=False,
    )
    appreciation = SimpleNamespace(
        id=uuid4(), role="President", document_type=DocumentType.END_OF_TENURE_APPRECIATION,
        signature_handling="retain", active=True, archived=False,
    )
    fields = [_field(name) for name in REQUIRED_LEADERSHIP_TEMPLATE_FIELDS]
    db = _RecognitionDb(
        scalar_values=[None, recognition, None, appreciation],
        scalar_lists=[[dsa, hod], fields, fields],
        rows=[(membership, student, None)],
    )

    plans = _preflight_session_recognition(db, session)

    assert [plan.document_type for plan in plans] == [
        DocumentType.LEADERSHIP_RECOGNITION,
        DocumentType.END_OF_TENURE_APPRECIATION,
    ]
    assert all(plan.signatories == (dsa, hod) for plan in plans)
    assert plans[0].values["student_name"] == "Ayesha Khan"
    assert plans[0].values["issue_date"] == date(2026, 8, 31)


def test_session_recognition_preflight_skips_existing_membership_letters() -> None:
    session = SimpleNamespace(id=uuid4(), name="2025-26", end_date=date(2026, 8, 31))
    membership = SimpleNamespace(
        id=uuid4(), student_id=uuid4(), role="President", start_date=date(2025, 9, 1),
        end_date=date(2026, 8, 31), status=MembershipStatus.COMPLETED,
    )
    db = _RecognitionDb(
        scalar_values=[uuid4(), uuid4()],
        scalar_lists=[[]],
        rows=[(membership, SimpleNamespace(), None)],
    )

    assert _preflight_session_recognition(db, session) == []
