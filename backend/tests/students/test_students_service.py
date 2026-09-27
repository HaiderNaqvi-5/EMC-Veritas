from uuid import uuid4

import pytest

from app.schemas.operations import StudentCreate
from app.services.students import create_student, deactivate_student, delete_inactive_student


class FakeDatabase:
    def __init__(self, existing=None) -> None:
        self.added = []
        self.flush_count = 0
        self.existing = existing

    def add(self, item) -> None:
        self.added.append(item)

    def scalar(self, _query):
        return self.existing

    def scalars(self, _query):
        return []

    def flush(self) -> None:
        self.flush_count += 1


class DeletionDatabase(FakeDatabase):
    def __init__(self, related_admin_ids=()) -> None:
        super().__init__()
        self.executed = []
        self.deleted = []
        self.related_admin_ids = related_admin_ids

    def scalars(self, _query):
        return self.related_admin_ids

    def execute(self, statement) -> None:
        self.executed.append(statement)

    def delete(self, item) -> None:
        self.deleted.append(item)


def test_create_student_trims_and_canonicalizes_identity_values() -> None:
    db = FakeDatabase()
    student = create_student(db, StudentCreate(roll_number="  2k22-bscs-238 ", full_name="  Ahmad Arshad  "))
    assert student.roll_number == "2K22-BSCS-238"
    assert student.full_name == "Ahmad Arshad"
    assert student.active is True
    assert db.added == [student]
    assert db.flush_count == 1


def test_deactivate_student_preserves_record() -> None:
    db = FakeDatabase()
    student = create_student(db, StudentCreate(roll_number="22-CS-2", full_name="Student"))
    result = deactivate_student(db, student)
    assert result is student
    assert student.active is False
    assert db.flush_count == 2


def test_create_student_reactivates_an_inactive_matching_roll_number() -> None:
    original = create_student(
        FakeDatabase(), StudentCreate(roll_number="2K22-BSCS-404", full_name="Old Name")
    )
    original.active = False
    db = FakeDatabase(existing=original)

    student = create_student(
        db, StudentCreate(roll_number="2k22-bscs-404", full_name="Updated Name")
    )

    assert student is original
    assert student.active is True
    assert student.full_name == "Updated Name"
    assert db.added == []
    assert db.flush_count == 1


def test_delete_inactive_student_removes_related_draft_links() -> None:
    db = DeletionDatabase()
    student = create_student(db, StudentCreate(roll_number="2K22-BSCS-999", full_name="Test Student"))
    deactivate_student(db, student)

    delete_inactive_student(db, student)

    assert db.deleted == [student]
    assert len(db.executed) == 3


def test_delete_inactive_student_detaches_audit_history_from_removed_admin() -> None:
    linked_admin_id = uuid4()
    db = DeletionDatabase([linked_admin_id])
    student = create_student(db, StudentCreate(roll_number="2K22-BSCS-998", full_name="Test Student"))
    deactivate_student(db, student)

    delete_inactive_student(db, student, protected_admin_id=uuid4())

    assert db.deleted == [student]
    assert len(db.executed) == 4


def test_delete_inactive_student_refuses_the_current_administrator() -> None:
    linked_admin_id = uuid4()
    db = DeletionDatabase([linked_admin_id])
    student = create_student(db, StudentCreate(roll_number="2K22-BSCS-997", full_name="Test Student"))
    deactivate_student(db, student)

    with pytest.raises(ValueError, match="own administrator"):
        delete_inactive_student(db, student, protected_admin_id=linked_admin_id)
