from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.admin.documents import (
    permanently_delete_activity_certificates,
    permanently_delete_student_documents,
    revoke_activity_certificates,
    revoke_student_activity_certificates,
)
from app.models.domain import DocumentStatus


def _document() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        status=DocumentStatus.VALID,
        verification_id=f"EMC-{uuid4().hex[:8].upper()}",
        version=1,
        storage_key=None,
    )


def test_activity_level_revocation_revokes_every_valid_certificate() -> None:
    activity = SimpleNamespace(id=uuid4())
    documents = [_document(), _document()]
    admin = SimpleNamespace(id=uuid4())
    db = Mock()
    db.get.return_value = activity
    db.scalars.return_value.all.return_value = documents

    result = revoke_activity_certificates(activity.id, db=db, admin=admin)

    assert result.activity_id == activity.id
    assert result.student_id is None
    assert result.revoked_document_ids == [document.id for document in documents]
    assert all(document.status is DocumentStatus.REVOKED for document in documents)
    # One audit record per certificate plus the activity-level audit event.
    assert db.add.call_count == 3
    db.commit.assert_called_once_with()


def test_student_level_revocation_only_targets_the_selected_student_certificate() -> None:
    activity = SimpleNamespace(id=uuid4())
    student_id = uuid4()
    document = _document()
    admin = SimpleNamespace(id=uuid4())
    db = Mock()
    db.get.return_value = activity
    db.scalars.return_value.all.return_value = [document]

    result = revoke_student_activity_certificates(
        activity.id,
        student_id,
        db=db,
        admin=admin,
    )

    assert result.activity_id == activity.id
    assert result.student_id == student_id
    assert result.revoked_document_ids == [document.id]
    assert document.status is DocumentStatus.REVOKED
    assert db.add.call_count == 2
    db.commit.assert_called_once_with()


def test_activity_level_revocation_rejects_an_unknown_activity() -> None:
    db = Mock()
    db.get.return_value = None

    with pytest.raises(HTTPException, match="Activity not found") as error:
        revoke_activity_certificates(uuid4(), db=db, admin=SimpleNamespace(id=uuid4()))

    assert error.value.status_code == 404
    db.scalars.assert_not_called()


def test_super_admin_can_permanently_delete_every_document_for_an_activity() -> None:
    activity = SimpleNamespace(id=uuid4())
    documents = [_document(), _document()]
    admin = SimpleNamespace(id=uuid4())
    db = Mock()
    db.get.return_value = activity
    db.scalars.return_value.all.return_value = documents

    result = permanently_delete_activity_certificates(activity.id, db=db, admin=admin)

    assert result.scope == "activity"
    assert result.activity_id == activity.id
    assert result.deleted_document_ids == [document.id for document in documents]
    assert db.delete.call_args_list == [((document,),) for document in documents]
    db.commit.assert_called_once_with()


def test_super_admin_can_permanently_delete_a_students_regular_and_leadership_documents() -> None:
    student = SimpleNamespace(id=uuid4())
    documents = [_document(), _document()]
    admin = SimpleNamespace(id=uuid4())
    db = Mock()
    db.get.return_value = student
    db.scalars.return_value.all.return_value = documents

    result = permanently_delete_student_documents(student.id, db=db, admin=admin)

    assert result.scope == "student"
    assert result.student_id == student.id
    assert result.deleted_document_ids == [document.id for document in documents]
    assert db.delete.call_args_list == [((document,),) for document in documents]
    db.commit.assert_called_once_with()
