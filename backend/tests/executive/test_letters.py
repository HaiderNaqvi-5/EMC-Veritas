from datetime import date
from types import SimpleNamespace

from app.services.executive.letters import leadership_fields_for_rendering, leadership_letter_values


def test_leadership_recipient_field_moves_above_its_underline_and_grows() -> None:
    source = SimpleNamespace(field_name="student_name", x=200, y=168, width=280, height=18)

    rendered = leadership_fields_for_rendering([source])[0]

    assert rendered is not source
    assert rendered.y == 150
    assert rendered.height == 32
    assert rendered.font_size == 24
    assert source.y == 168
    assert source.height == 18


def test_overall_ec_roles_do_not_receive_a_society_name() -> None:
    overall_roles = (
        "President", "Vice President", "Deputy Vice President", "Director of Club Operations (DCO)",
        "Finance Head", "General Secretary", "External Affairs",
    )
    for role in overall_roles:
        values = leadership_letter_values(
            student_name="Ayesha Khan", roll_number="2K22-BSCS-404", role=role,
            society_name="Media & Graphics", role_start_date=date(2025, 5, 1),
            role_end_date=date(2026, 7, 31), session_name="2K22", issue_date=date(2026, 7, 31),
        )
        assert values["society_name"] == ""


def test_society_head_retains_their_society_name() -> None:
    values = leadership_letter_values(
        student_name="Ayesha Khan", roll_number="2K22-BSCS-404", role="Society Head",
        society_name="Media & Graphics", role_start_date=date(2025, 5, 1),
        role_end_date=date(2026, 7, 31), session_name="2K22", issue_date=date(2026, 7, 31),
    )
    assert values["society_name"] == "Media & Graphics"
