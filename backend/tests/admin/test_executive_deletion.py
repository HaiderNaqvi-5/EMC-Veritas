from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.admin.executive import delete_removed_membership
from app.models.domain import MembershipStatus


def test_permanent_membership_deletion_removes_revoked_document_dependencies() -> None:
    membership = SimpleNamespace(id=uuid4(), status=MembershipStatus.REMOVED)
    db = Mock()
    db.get.return_value = membership
    # No non-revoked document exists, so revoked records must be cleaned up.
    db.scalar.return_value = None

    delete_removed_membership(membership.id, db=db)

    assert db.execute.call_count == 2
    db.delete.assert_called_once_with(membership)
    db.commit.assert_called_once_with()


def test_permanent_membership_deletion_still_blocks_active_documents() -> None:
    membership = SimpleNamespace(id=uuid4(), status=MembershipStatus.REMOVED)
    db = Mock()
    db.get.return_value = membership
    db.scalar.return_value = uuid4()

    with pytest.raises(HTTPException, match="active issued leadership documents") as error:
        delete_removed_membership(membership.id, db=db)

    assert error.value.status_code == 409
    db.execute.assert_not_called()
    db.delete.assert_not_called()
