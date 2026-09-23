from types import SimpleNamespace

import pytest

from app.models.domain import MembershipStatus, SessionStatus
from app.services.executive.constants import EXECUTIVE_ROLES, SOCIETIES
from app.services.executive.recognition import memberships_eligible_for_session_recognition
from app.services.executive.validation import validate_membership


def test_v1_executive_roles_and_societies_are_exact() -> None:
    assert EXECUTIVE_ROLES == {
        "President", "Vice President", "Deputy Vice President", "General Secretary",
        "Finance Head", "Director of Club Operations (DCO)", "External Affairs", "Society Head",
    }
    assert SOCIETIES == {"Social Welfare", "SciTech", "Arts & Decor", "Media & Graphics", "Discipline"}


@pytest.mark.parametrize("role", EXECUTIVE_ROLES)
def test_non_society_roles_cannot_claim_a_society(role: str) -> None:
    if role == "Society Head":
        validate_membership(role, "SciTech")
    else:
        validate_membership(role, None)
        with pytest.raises(ValueError, match="Only Society Head"):
            validate_membership(role, "SciTech")


def test_invalid_role_or_society_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        validate_membership("Coordinator", None)
    with pytest.raises(ValueError, match="approved society"):
        validate_membership("Society Head", "Robotics")


def test_recognition_is_limited_to_completed_members_after_session_close() -> None:
    completed = SimpleNamespace(status=MembershipStatus.COMPLETED)
    active = SimpleNamespace(status=MembershipStatus.ACTIVE)
    removed = SimpleNamespace(status=MembershipStatus.REMOVED)

    assert memberships_eligible_for_session_recognition(
        [completed, active, removed], SessionStatus.ACTIVE
    ) == []
    assert memberships_eligible_for_session_recognition(
        [completed, active, removed], SessionStatus.CLOSED
    ) == [completed]
