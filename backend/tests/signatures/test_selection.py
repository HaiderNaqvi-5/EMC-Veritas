from datetime import date
from types import SimpleNamespace
from uuid import UUID

from app.services.signatures.availability import select_effective_signatories
from app.services.signatures.rendering import missing_signature_fields, signature_field_name


def _signatory(identifier: int, title: str, start: date, end: date | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=UUID(int=identifier),
        official_title=title,
        effective_start_date=start,
        effective_end_date=end,
        active=True,
    )


def test_select_effective_signatories_uses_latest_eligible_record_per_title() -> None:
    older = _signatory(1, "President", date(2026, 1, 1), date(2026, 6, 30))
    current = _signatory(2, "President", date(2026, 7, 1))
    dsa = _signatory(3, "DSA", date(2026, 1, 1))

    selected = select_effective_signatories(
        [older, current, dsa], ("President", "DSA"), date(2026, 9, 1)
    )

    assert selected == {"President": current, "DSA": dsa}


def test_signature_field_names_require_positions_for_every_selected_title() -> None:
    fields = [SimpleNamespace(field_name="signature_president")]

    assert signature_field_name("DSA") == "signature_dsa"
    assert missing_signature_fields(fields, ["President", "DSA"]) == ["signature_dsa"]
