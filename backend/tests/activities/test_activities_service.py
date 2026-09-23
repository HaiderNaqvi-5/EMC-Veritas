from datetime import date
from uuid import uuid4

import pytest

from app.models.domain import Student
from app.schemas.operations import ActivityCreate, ActivityUpdate
from app.services.activities import add_participant, create_activity, update_activity


class FakeDatabase:
    def __init__(self, student: Student | None = None) -> None:
        self.student = student
        self.added = []
        self.flush_count = 0

    def add(self, item) -> None:
        self.added.append(item)

    def get(self, model, identifier):
        return self.student if model is Student else None

    def flush(self) -> None:
        self.flush_count += 1


def test_create_and_update_activity() -> None:
    db = FakeDatabase()
    activity = create_activity(db, ActivityCreate(session_id=uuid4(), name="Welcome", description="Initial", activity_date=date(2026, 2, 1)), uuid4())
    assert activity.name == "Welcome"
    assert activity.description == "Initial"
    update_activity(db, activity, ActivityUpdate(name="Updated", description=None, activity_date=date(2026, 2, 2)))
    assert activity.name == "Updated"
    assert activity.description is None
    assert activity.activity_date == date(2026, 2, 2)


def test_add_participant_requires_existing_student() -> None:
    with pytest.raises(LookupError):
        add_participant(FakeDatabase(), uuid4(), uuid4())


def test_add_participant_defaults_to_eligible() -> None:
    student = Student(id=uuid4(), roll_number="22-CS-3", full_name="Participant", active=True)
    db = FakeDatabase(student)
    participant = add_participant(db, uuid4(), student.id)
    assert participant.student_id == student.id
    assert participant.eligible is True
    assert db.added == [participant]
