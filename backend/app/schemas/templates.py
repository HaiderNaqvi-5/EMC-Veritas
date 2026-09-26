from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TemplateFieldInput(BaseModel):
    field_name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,79}$")
    page_number: int = Field(ge=1)
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    font_family: Literal["helv", "tiro", "cour", "custom"] = "helv"
    custom_font_id: UUID | None = None
    font_size: int | None = Field(default=None, ge=5, le=72)
    text_color: str = Field(default="#000000", pattern=r"^#[0-9A-Fa-f]{6}$")


class TemplateFieldsCreate(BaseModel):
    fields: list[TemplateFieldInput] = Field(min_length=1)
    signature_handling: Literal["retain", "replace"]


class TemplateFieldResponse(BaseModel):
    """Persisted placement data for a certificate template field."""

    model_config = ConfigDict(from_attributes=True)

    field_name: str
    page_number: int
    x: int
    y: int
    width: int
    height: int
    font_family: Literal["helv", "tiro", "cour", "custom"]
    font_size: int | None
    text_color: str


class TemplateResponse(BaseModel):
    id: UUID
    name: str
    approved: bool
    archived: bool
    signature_handling: Literal["retain", "replace"] | None
    created_at: datetime


class TemplateFontResponse(BaseModel):
    id: UUID
    name: str
    content_type: Literal["font/ttf", "font/otf"]
    created_at: datetime


class DetectedTemplateFieldResponse(BaseModel):
    field_name: str
    page_number: int
    x: int
    y: int
    width: int
    height: int
    detected_text: str


class TemplateAnalysisResponse(BaseModel):
    page_count: int
    extracted_text: list[str]
    ocr_used: bool
    ocr_required: bool
    signature_content_detected: bool
    detected_fields: list[DetectedTemplateFieldResponse]


class TemplatePreviewRequest(BaseModel):
    student_id: UUID
    activity_id: UUID
