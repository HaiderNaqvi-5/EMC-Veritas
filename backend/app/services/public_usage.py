import hashlib
import hmac
from typing import Literal

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models.domain import PublicStudentUsage

UsageEvent = Literal["lookup", "download"]


def student_fingerprint(roll_number: str) -> str:
    """Return a stable one-way identifier without retaining the roll number."""

    return hmac.new(
        settings.session_secret.encode("utf-8"),
        roll_number.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def record_public_usage(db: Session, *, roll_number: str, event: UsageEvent) -> None:
    fingerprint = student_fingerprint(roll_number)
    now = func.now()
    values: dict[str, object] = {
        "student_fingerprint": fingerprint,
        "lookup_count": 0,
        "download_count": 0,
    }
    if event == "lookup":
        values.update(lookup_count=1, first_lookup_at=now, last_lookup_at=now)
        update_values = {
            "lookup_count": PublicStudentUsage.lookup_count + 1,
            "first_lookup_at": func.coalesce(PublicStudentUsage.first_lookup_at, now),
            "last_lookup_at": now,
            "updated_at": now,
        }
    else:
        values.update(download_count=1, first_download_at=now, last_download_at=now)
        update_values = {
            "download_count": PublicStudentUsage.download_count + 1,
            "first_download_at": func.coalesce(PublicStudentUsage.first_download_at, now),
            "last_download_at": now,
            "updated_at": now,
        }
    statement = insert(PublicStudentUsage).values(**values).on_conflict_do_update(
        index_elements=[PublicStudentUsage.student_fingerprint],
        set_=update_values,
    )
    db.execute(statement)
