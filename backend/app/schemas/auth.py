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
