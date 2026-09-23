from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TemplateFieldInput(BaseModel):
    field_name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,79}$")
    page_number: int = Field(ge=1)
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class TemplateFieldsCreate(BaseModel):
    fields: list[TemplateFieldInput] = Field(min_length=1)


class TemplateResponse(BaseModel):
    id: UUID
    name: str
    approved: bool
    archived: bool
    created_at: datetime


class TemplateAnalysisResponse(BaseModel):
    page_count: int
    extracted_text: list[str]
    ocr_required: bool


class TemplatePreviewRequest(BaseModel):
    student_id: UUID
    activity_id: UUID
