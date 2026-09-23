from datetime import date

from app.services.signatures.availability import missing_titles


def test_effective_signatory_can_be_selected_from_multiple_historical_records() -> None:
    available = {
        "President": [(date(2026, 1, 1), date(2026, 4, 30)), (date(2026, 5, 1), None)],
        "DSA": [(date(2026, 1, 1), None)],
    }
    assert missing_titles(("President", "DSA"), available, date(2026, 9, 1)) == []


def test_missing_titles_are_precise() -> None:
    assert missing_titles(("President", "DSA"), {}, date(2026, 9, 1)) == ["President", "DSA"]
