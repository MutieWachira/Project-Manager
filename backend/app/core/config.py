from functools import lru_cache
from pathlib import Path
from typing import Literal

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    APP_NAME: str = "SherlskyyCommand"
    APP_VERSION: str = (PROJECT_ROOT / "version.txt").read_text(
        encoding="utf-8"
    ).strip()
    APP_ENV: str = "development"

    API_V1_PREFIX: str = "/api/v1"

    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000

    FRONTEND_URL: str = "http://localhost:3000"

    # GitHub App integration. These remain optional until the app is configured.
    GITHUB_APP_ID: str | None = None
    GITHUB_APP_SLUG: str | None = None
    GITHUB_APP_PRIVATE_KEY_PATH: Path | None = None
    GITHUB_APP_CLIENT_ID: str | None = None
    GITHUB_APP_CLIENT_SECRET: SecretStr | None = None
    GITHUB_APP_CALLBACK_URL: str | None = None
    GITHUB_APP_SETUP_URL: str | None = None
    GITHUB_APP_WEBHOOK_SECRET: SecretStr | None = None

    DATABASE_URL: str = Field(
        default="postgresql+psycopg://localhost/sherlskyycommand_db"
    )

    # JWT authentication
    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    MFA_ENCRYPTION_KEY: SecretStr

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=10,
        ge=1,
        le=30,
    )

    # Authentication session configuration
    SESSION_EXPIRE_DAYS: int = Field(
        default=30,
        ge=1,
        le=90,
    )

    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=30,
        ge=1,
        le=90,
    )

    REFRESH_TOKEN_COOKIE_NAME: str = "sherlskyycommand_refresh"
    REFRESH_TOKEN_COOKIE_PATH: str = "/api/v1/auth"
    REFRESH_TOKEN_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    @property
    def refresh_token_cookie_secure(self) -> bool:
        """Require HTTPS for refresh cookies in production."""
        return self.APP_ENV.casefold() == "production"

    JWT_ISSUER: str = "SherlskyyCommand"
    JWT_AUDIENCE: str = "SherlskyyCommand"

    @field_validator("MFA_ENCRYPTION_KEY")
    @classmethod
    def validate_mfa_encryption_key(cls, value: SecretStr) -> SecretStr:
        try:
            Fernet(value.get_secret_value().encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise ValueError("MFA encryption key must be a valid Fernet key.") from exc

        return value

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 64:
            raise ValueError("JWT signing secret must contain at least 64 characters.")

        return value

    @field_validator("GITHUB_APP_ID")
    @classmethod
    def validate_github_app_id(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        if not value.isdigit():
            raise ValueError("GitHub App ID must contain digits only.")

        return value

    @field_validator("GITHUB_APP_SLUG")
    @classmethod
    def validate_github_app_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        if not value or any(
            not (character.islower() or character.isdigit() or character == "-")
            for character in value
        ):
            raise ValueError("GitHub App slug must use lowercase letters, digits, and hyphens.")

        return value

    @field_validator("GITHUB_APP_PRIVATE_KEY_PATH")
    @classmethod
    def validate_github_private_key_path(
        cls,
        value: Path | None,
    ) -> Path | None:
        if value is None:
            return None

        value = value.expanduser()
        if not value.is_absolute():
            raise ValueError("GitHub App private key path must be absolute.")

        try:
            value.resolve().relative_to(PROJECT_ROOT.resolve())
        except ValueError:
            return value

        raise ValueError("GitHub App private key must be stored outside the project directory.")

    @property
    def github_app_ready(self) -> bool:
        """Return whether the minimum GitHub App credentials are available."""
        if not all((
            self.GITHUB_APP_ID,
            self.GITHUB_APP_SLUG,
            self.GITHUB_APP_PRIVATE_KEY_PATH,
            self.GITHUB_APP_CLIENT_ID,
            self.GITHUB_APP_CLIENT_SECRET,
            self.GITHUB_APP_CALLBACK_URL,
            self.GITHUB_APP_SETUP_URL,
        )):
            return False

        key_path = self.GITHUB_APP_PRIVATE_KEY_PATH
        if key_path is None or not key_path.is_file():
            return False

        try:
            import stat

            permissions = stat.S_IMODE(key_path.stat().st_mode)
        except OSError:
            return False

        return permissions & 0o077 == 0

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
