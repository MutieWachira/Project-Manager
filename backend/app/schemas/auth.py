"""Pydantic schemas for authentication requests and responses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Validate a new account registration request."""

    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    @field_validator("full_name", mode="before")
    @classmethod
    def normalize_full_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().casefold()
        return value


class RegistrationResponse(BaseModel):
    """Response returned after a registration request."""

    message: str


class VerifyEmailRequest(BaseModel):
    """Validate an email verification request."""

    token: str = Field(min_length=20, max_length=256)


class VerifyEmailResponse(BaseModel):
    """Response returned after email verification."""

    message: str


class LoginRequest(BaseModel):
    """Validate a password-based login request."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    client_type: Literal["web", "mobile"] = "web"
    device_name: str | None = Field(default=None, max_length=120)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().casefold()
        return value

    @field_validator("device_name")
    @classmethod
    def normalize_device_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None


class MFAChallengeVerifyRequest(BaseModel):
    """Validate an MFA login challenge verification request."""

    challenge_token: str = Field(min_length=20, max_length=4096)
    code: str = Field(min_length=1, max_length=32)
    device_name: str | None = Field(default=None, max_length=120)

    @field_validator("device_name")
    @classmethod
    def normalize_device_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None


class LoginResponse(BaseModel):
    """Represent either an MFA challenge or a completed login."""

    mfa_required: bool = False
    challenge_token: str | None = None
    challenge_expires_at: datetime | None = None

    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None

    session_id: str | None = None
    session_expires_at: datetime | None = None


class RefreshRequest(BaseModel):
    """Validate a mobile refresh-token request."""

    refresh_token: str = Field(min_length=32, max_length=256)


class RefreshResponse(BaseModel):
    """Represent a successfully refreshed authentication session."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int
    session_id: str
    session_expires_at: datetime


class LogoutRequest(BaseModel):
    """Validate a mobile logout request."""

    refresh_token: str = Field(min_length=32, max_length=256)


class LogoutResponse(BaseModel):
    """Represent a successful logout."""

    message: str


class CurrentUserResponse(BaseModel):
    """Safe public representation of the authenticated user."""

    id: str
    full_name: str
    email: EmailStr
    is_active: bool
    email_verified: bool
