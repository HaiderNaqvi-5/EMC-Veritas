from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    roll_number: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class AdminSessionResponse(BaseModel):
    authenticated: bool
    role: str | None = None
    temporary_password_change_required: bool = False


class AdminAccountCreate(BaseModel):
    student_id: UUID
    role: str = Field(pattern=r"^(ADMIN|SUPER_ADMIN)$")
    temporary_password: str = Field(min_length=12, max_length=256)


class AdminAccountResponse(BaseModel):
    id: UUID
    student_id: UUID
    roll_number: str
    full_name: str
    role: str
    active: bool
    must_change_password: bool


class AdminPasswordReset(BaseModel):
    temporary_password: str = Field(min_length=12, max_length=256)


class StudentAccountRequest(BaseModel):
    roll_number: str = Field(min_length=1, max_length=64)


class StudentActivationLookup(StudentAccountRequest):
    full_name: str = Field(min_length=2, max_length=255)


class StudentActivationHint(BaseModel):
    email_hint: str | None = None


class StudentActivationConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=12, max_length=256)


class StudentLoginRequest(LoginRequest):
    pass


class StudentRecoveryRequest(StudentAccountRequest):
    requested_email: str = Field(min_length=3, max_length=320)
    reason: str = Field(min_length=10, max_length=500)

    @field_validator("requested_email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        local, separator, domain = value.rpartition("@")
        if not local or not separator or "." not in domain:
            raise ValueError("A valid email address is required")
        return value


class StudentSessionResponse(BaseModel):
    authenticated: bool
    full_name: str | None = None
    roll_number: str | None = None


class EmailRecoveryRequestResponse(BaseModel):
    id: UUID
    student_id: UUID
    roll_number: str
    full_name: str
    requested_email: str
    reason: str
    status: str
    created_at: datetime
