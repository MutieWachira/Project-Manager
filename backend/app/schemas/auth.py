
"""Pydantic schemas for authentication requests and responses."""

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
    """Validate a login request."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().casefold()
        return value


class LoginResponse(BaseModel):
    """Return an authenticated access token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int

class CurrentUserResponse(BaseModel):
    """Safe public representation of the authenticated user."""

    id: str
    full_name: str
    email: EmailStr
    is_active: bool
    email_verified: bool