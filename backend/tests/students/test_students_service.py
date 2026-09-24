from app.schemas.operations import StudentCreate
from app.services.students import create_student, deactivate_student


class FakeDatabase:
    def __init__(self) -> None:
        self.added = []
        self.flush_count = 0

    def add(self, item) -> None:
        self.added.append(item)

    def flush(self) -> None:
        self.flush_count += 1


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
