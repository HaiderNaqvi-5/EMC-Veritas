from datetime import date

from app.models.domain import SessionStatus
from app.schemas.operations import SessionCreate, SessionUpdate
from app.services.sessions import close_session, create_session, update_session


class FakeDatabase:
    def __init__(self) -> None:
        self.added = []
        self.flush_count = 0

    def add(self, item) -> None:
        self.added.append(item)

    def flush(self) -> None:
        self.flush_count += 1


def test_create_close_and_update_session_without_deleting_history() -> None:
    db = FakeDatabase()
    session = create_session(db, SessionCreate(name="  2026 Session ", start_date=date(2026, 1, 1), end_date=date(2026, 8, 30)))
    assert session.name == "2026 Session"
    assert session.status == SessionStatus.ACTIVE
    update_session(db, session, SessionUpdate(name="2026-27", start_date=date(2026, 1, 2), end_date=date(2026, 8, 30)))
    assert session.name == "2026-27"
    assert session.start_date == date(2026, 1, 2)
    close_session(db, session)
    assert session.status == SessionStatus.CLOSED
    assert db.added == [session]
    assert db.flush_count == 3
