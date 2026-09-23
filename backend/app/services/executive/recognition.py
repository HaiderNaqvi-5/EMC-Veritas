from collections.abc import Iterable

from app.models.domain import DocumentType, ExecutiveMembership, MembershipStatus, SessionStatus

RECOGNITION_DOCUMENT_TYPES = (
    DocumentType.LEADERSHIP_RECOGNITION,
    DocumentType.END_OF_TENURE_APPRECIATION,
)


def memberships_eligible_for_session_recognition(
    memberships: Iterable[ExecutiveMembership], session_status: SessionStatus
) -> list[ExecutiveMembership]:
    """Recognition is available only after a session closes, never for removals."""
    if session_status is not SessionStatus.CLOSED:
        return []
    return [membership for membership in memberships if membership.status is MembershipStatus.COMPLETED]
