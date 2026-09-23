from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import MembershipStatus


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StudentCreate(APIModel):
    roll_number: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=1, max_length=255)


class StudentResponse(StudentCreate):
    id: UUID
    active: bool
    created_at: datetime
    updated_at: datetime


class SessionCreate(APIModel):
    name: str = Field(min_length=1, max_length=150)
    start_date: date
    end_date: date


class SessionUpdate(SessionCreate):
    pass


class SessionResponse(SessionCreate):
    id: UUID
    status: str


class ActivityCreate(APIModel):
    session_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    activity_date: date
    template_id: UUID | None = None


class ActivityUpdate(APIModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    activity_date: date
    template_id: UUID | None = None


class ActivityResponse(ActivityCreate):
    id: UUID
    issue_date: date | None
    status: str


class ImportPreviewRow(APIModel):
    row_number: int
    roll_number: str | None
    full_name: str | None
    outcome: str
    detail: str | None = None


class ImportPreview(APIModel):
    valid_rows: int
    duplicate_rows: int
    conflicting_rows: int
    invalid_rows: int
    rows: list[ImportPreviewRow]


class ImportCommitRow(APIModel):
    roll_number: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=1, max_length=255)
    conflict_resolution: str | None = None


class ImportCommit(APIModel):
    rows: list[ImportCommitRow]


class SocietyResponse(APIModel):
    id: UUID
    name: str
    active: bool


class ExecutiveMembershipCreate(APIModel):
    student_id: UUID
    session_id: UUID
    role: str = Field(min_length=1, max_length=80)
    society_id: UUID | None = None
    start_date: date
    end_date: date | None = None
    status: MembershipStatus = MembershipStatus.ACTIVE


class ExecutiveMembershipUpdate(APIModel):
    role: str | None = Field(default=None, min_length=1, max_length=80)
    society_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: MembershipStatus | None = None


class ExecutiveMembershipResponse(APIModel):
    id: UUID
    student_id: UUID
    student_name: str
    roll_number: str
    session_id: UUID
    session_name: str
    society_id: UUID | None
    society_name: str | None
    role: str
    start_date: date
    end_date: date | None
    status: MembershipStatus
