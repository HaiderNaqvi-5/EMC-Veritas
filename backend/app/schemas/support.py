from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.models.domain import SupportRequestStatus
from app.services.students import normalize_roll_number

SupportCategory = Literal[
    "MISSING_RECORD",
    "MISSING_CERTIFICATE",
    "INCORRECT_DETAILS",
    "DOWNLOAD_PROBLEM",
    "OTHER",
]


class SupportRequestCreate(BaseModel):
    roll_number: str = Field(min_length=3, max_length=64)
    full_name: str = Field(min_length=2, max_length=255)
    contact_email: str = Field(
        min_length=5,
        max_length=320,
        pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    )
    problem_category: SupportCategory
    problem_details: str = Field(min_length=15, max_length=2000)
    website: str = Field(default="", max_length=200)

    @field_validator("roll_number")
    @classmethod
    def normalize_roll(cls, value: str) -> str:
        normalized = normalize_roll_number(value)
        if len(normalized) < 3:
            raise ValueError("Enter a valid roll number")
        return normalized

    @field_validator("full_name", "contact_email", "problem_details")
    @classmethod
    def trim_text(cls, value: str, info: ValidationInfo) -> str:
        cleaned = value.strip()
        minimum = 15 if info.field_name == "problem_details" else 2
        if len(cleaned) < minimum:
            raise ValueError(f"This field must contain at least {minimum} characters")
        return cleaned

    @field_validator("contact_email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class SupportRequestCreated(BaseModel):
    ticket_number: str
    status: SupportRequestStatus


class SupportRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticket_number: str
    roll_number: str
    full_name: str
    contact_email: str
    problem_category: str
    problem_details: str
    status: SupportRequestStatus
    admin_notes: str | None
    resolution_message: str | None
    resolved_by_admin_id: UUID | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SupportRequestUpdate(BaseModel):
    status: SupportRequestStatus
    admin_notes: str | None = Field(default=None, max_length=4000)
    resolution_message: str | None = Field(default=None, max_length=4000)

    @field_validator("admin_notes", "resolution_message")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
