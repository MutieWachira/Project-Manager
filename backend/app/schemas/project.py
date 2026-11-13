"""Pydantic schemas for project API responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ProjectStatus

class ProjectCreate(BaseModel):
    """Validated input for creating  project"""
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )
    name: str = Field(min_length=2, max_length=150)
    description: str| None = Field(default=None, max_length=2000)

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value:str | None) -> str | None:
        """Convert blank descriptions to None and trim surrounding spaces"""
        if value is None:
            return None

        cleaned = value.strip()
        return cleaned or None

class ProjectRead(BaseModel):
    """Public project representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: str | None
    status: ProjectStatus
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime
