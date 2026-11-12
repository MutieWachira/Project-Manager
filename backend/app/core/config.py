from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    APP_NAME: str = "SherlskyyCommand"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"

    API_V1_PREFIX: str = "/api/v1"

    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000

    FRONTEND_URL: str = "http://localhost:3000"

    DATABASE_URL: str = Field(
        default="postgresql+psycopg://localhost/sherlskyycommand_db"
    )

    # JWT authentication
    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: Literal["HS256"] = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=10,
        ge=1,
        le=30,
    )

    JWT_ISSUER: str = "SherlskyyCommand"
    JWT_AUDIENCE: str = "SherlskyyCommand"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 64:
            raise ValueError(
                "JWT signing secret must contain at least 64 characters."
            )

        return value

    # Email configuration
    MAIL_HOST: str = "127.0.0.1"
    MAIL_PORT: int = 1025
    MAIL_USERNAME: str | None = None
    MAIL_PASSWORD: str | None = None
    MAIL_FROM: str = "no-reply@sherlskyycommand.local"
    MAIL_FROM_NAME: str = "SherlskyyCommand"
    MAIL_STARTTLS: bool = False
    MAIL_TIMEOUT: int = 10

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()