from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.admin.activities import permanently_delete_archived_activity
from app.models.domain import ActivityStatus


def test_super_admin_can_permanently_delete_an_archived_activity_and_its_documents() -> None:
    activity = SimpleNamespace(id=uuid4(), name="Orientation Week", status=ActivityStatus.ARCHIVED)
    documents = [SimpleNamespace(id=uuid4(), storage_key=None), SimpleNamespace(id=uuid4(), storage_key=None)]
    db = Mock()
    db.get.return_value = activity
    db.scalars.return_value.all.return_value = documents

    permanently_delete_archived_activity(activity.id, admin=SimpleNamespace(id=uuid4()), db=db)

    # Dependents are removed in SQL before the activity itself, avoiding a
    # foreign-key violation when issued documents have signatory snapshots.
    assert db.execute.call_count == 4
    assert db.delete.call_args_list == [((activity,),)]
    db.commit.assert_called_once_with()


def test_permanent_activity_deletion_requires_archiving_first() -> None:
    activity = SimpleNamespace(id=uuid4(), name="Orientation Week", status=ActivityStatus.PUBLISHED)
    db = Mock()
    db.get.return_value = activity

    with pytest.raises(HTTPException, match="Archive the activity") as error:
        permanently_delete_archived_activity(activity.id, admin=SimpleNamespace(id=uuid4()), db=db)

    assert error.value.status_code == 409
    db.scalars.assert_not_called()
