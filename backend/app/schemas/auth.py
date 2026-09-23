from uuid import UUID

from pydantic import BaseModel, Field


class AdminLookupRequest(BaseModel):
    roll_number: str = Field(min_length=1, max_length=64)


class AdminLookupResponse(BaseModel):
    is_admin: bool
    active: bool


class LoginRequest(AdminLookupRequest):
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
