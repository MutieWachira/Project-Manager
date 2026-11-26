"""Pydantic schemas for project operational resources."""

from datetime import datetime
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.models.enums import EnvironmentType, IntegrationStatus, IntegrationType


class EnvironmentCreate(BaseModel):
    """Input for creating a project environment."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str = Field(min_length=2, max_length=100)
    environment_type: EnvironmentType = EnvironmentType.DEVELOPMENT
    description: str | None = Field(default=None, max_length=2000)
    base_url: str | None = Field(default=None, max_length=500)
    is_primary: bool = False
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value:
            raise ValueError("Environment name cannot be blank.")
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()
        if not cleaned:
            return None

        # HTTP is allowed for local development environments.
        parsed = AnyHttpUrl(cleaned)
        return str(parsed)


class EnvironmentUpdate(BaseModel):
    """Input for partially updating an environment."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str | None = Field(default=None, min_length=2, max_length=100)
    environment_type: EnvironmentType | None = None
    description: str | None = Field(default=None, max_length=2000)
    base_url: str | None = Field(default=None, max_length=500)
    is_primary: bool | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("Environment name cannot be blank.")
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()
        if not cleaned:
            return None

        parsed = AnyHttpUrl(cleaned)
        return str(parsed)


class EnvironmentRead(BaseModel):
    """Public representation of a project environment."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    environment_type: EnvironmentType
    description: str | None
    base_url: str | None
    is_primary: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class IntegrationCreate(BaseModel):
    """Input for registering a project integration."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str = Field(min_length=2, max_length=150)
    integration_type: IntegrationType
    environment_id: UUID | None = None
    external_reference: str | None = Field(default=None, max_length=500)


class IntegrationUpdate(BaseModel):
    """Input for updating a project integration."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str | None = Field(default=None, min_length=2, max_length=150)
    environment_id: UUID | None = None
    external_reference: str | None = Field(default=None, max_length=500)


class IntegrationRead(BaseModel):
    """Safe public representation of a project integration."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    environment_id: UUID | None
    integration_type: IntegrationType
    name: str
    external_reference: str | None
    status: IntegrationStatus
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime
