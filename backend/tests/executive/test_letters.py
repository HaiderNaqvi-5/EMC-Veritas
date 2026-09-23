from datetime import date

from app.services.executive.letters import (
    REQUIRED_LEADERSHIP_FIELDS,
    leadership_letter_values,
    missing_leadership_fields,
)


def test_leadership_template_requires_only_fixed_record_placeholders() -> None:
    assert missing_leadership_fields(set()) == REQUIRED_LEADERSHIP_FIELDS
    assert missing_leadership_fields(set(REQUIRED_LEADERSHIP_FIELDS)) == set()


def test_leadership_letter_values_are_deterministic_and_never_ai_generated() -> None:
    values = leadership_letter_values(
        student_name="Ayesha Khan",
        roll_number="FA21-BCS-001",
        role="Society Head",
        society_name="SciTech",
        role_start_date=date(2025, 9, 1),
        role_end_date=date(2026, 6, 30),
        session_name="2025–26",
        issue_date=date(2026, 7, 1),
    )

    assert set(values) == REQUIRED_LEADERSHIP_FIELDS
    assert values["society_name"] == "SciTech"
    assert values["issue_date"] == date(2026, 7, 1)
