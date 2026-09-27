from collections.abc import Iterable, Mapping
from copy import copy
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
# The verification identifier is rendered directly below the QR code.  The QR
# code remains the verification link; the printed ID gives recipients a
# practical fallback for checking a leadership letter manually.
REQUIRED_LEADERSHIP_TEMPLATE_FIELDS = REQUIRED_LEADERSHIP_FIELDS | {"qr_code", "verification_id"}


def missing_leadership_fields(field_names: set[str]) -> set[str]:
    return REQUIRED_LEADERSHIP_FIELDS - field_names


def missing_leadership_template_fields(field_names: set[str]) -> set[str]:
    """Include the required QR placement in addition to fixed record placeholders."""
    return REQUIRED_LEADERSHIP_TEMPLATE_FIELDS - field_names


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


def leadership_fields_for_rendering(fields: Iterable[object]) -> list[object]:
    """Apply the Leadership letter's recipient-name geometry at render time.

    Leadership PDFs put the name marker immediately above an existing rule.
    The detected marker box is too close to that rule for a prominent name, so
    shift the actual field upward and enlarge it without mutating the saved
    editor coordinates or requiring an active template to be recreated.
    """
    prepared = []
    for field in fields:
        if getattr(field, "field_name", None) != "student_name" or not all(
            hasattr(field, attribute) for attribute in ("y", "height")
        ):
            prepared.append(field)
            continue
        adjusted = copy(field)
        adjusted.y = max(0, field.y - 18)
        adjusted.height = max(field.height, 32)
        adjusted.font_size = 24
        prepared.append(adjusted)
    return prepared
