from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
