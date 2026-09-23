from collections.abc import Mapping
from datetime import date

REQUIRED_LEADERSHIP_FIELDS = frozenset(
    {
        "student_name",
        "roll_number",
        "role",
        "society_name",
        "role_start_date",
        "role_end_date",
        "session_name",
        "issue_date",
    }
)


def missing_leadership_fields(field_names: set[str]) -> set[str]:
    return REQUIRED_LEADERSHIP_FIELDS - field_names


def leadership_letter_values(
    *,
    student_name: str,
    roll_number: str,
    role: str,
    society_name: str | None,
    role_start_date: date,
    role_end_date: date,
    session_name: str,
    issue_date: date,
) -> Mapping[str, str | date]:
    """Return the complete fixed-record substitution set for V1 letters."""
    return {
        "student_name": student_name,
        "roll_number": roll_number,
        "role": role,
        "society_name": society_name or "",
        "role_start_date": role_start_date,
        "role_end_date": role_end_date,
        "session_name": session_name,
        "issue_date": issue_date,
    }
