from types import SimpleNamespace

from app.api.admin.ec_certificates import _ec_reissue_state
from app.models.domain import DocumentStatus


def test_ec_reissue_increments_latest_version_and_selects_valid_predecessor() -> None:
    superseded = SimpleNamespace(version=1, status=DocumentStatus.SUPERSEDED)
    current = SimpleNamespace(version=2, status=DocumentStatus.VALID)

    version, predecessors = _ec_reissue_state([current, superseded])

    assert version == 3
    assert predecessors == [current]


def test_first_ec_issue_starts_at_version_one_without_a_predecessor() -> None:
    version, predecessors = _ec_reissue_state([])

    assert version == 1
    assert predecessors == []


def test_ec_issue_after_revocation_preserves_history_without_superseding_it() -> None:
    revoked = SimpleNamespace(version=4, status=DocumentStatus.REVOKED)

    version, predecessors = _ec_reissue_state([revoked])

    assert version == 5
    assert predecessors == []
