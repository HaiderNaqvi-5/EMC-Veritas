from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

LeadershipDocumentType = Literal["LEADERSHIP_RECOGNITION", "END_OF_TENURE_APPRECIATION"]


class LeadershipTemplateFieldInput(BaseModel):
    field_name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,79}$")
    page_number: int = Field(ge=1)
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class LeadershipTemplateFieldsCreate(BaseModel):
    fields: list[LeadershipTemplateFieldInput] = Field(min_length=1)
    signature_handling: Literal["retain", "replace"]


class LeadershipTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    role: str
    document_type: LeadershipDocumentType
    signature_handling: Literal["retain", "replace"] | None
    active: bool
    archived: bool
    created_at: datetime
