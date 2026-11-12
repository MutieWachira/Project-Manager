"""JWT access-token creation and validation."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from jose import JWTError, jwt

from app.core.config import settings


class InvalidTokenError(ValueError):
    """Raised when an access token is invalid or cannot be verified."""


def create_access_token(
    subject: str,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token for a user."""

    if not subject or not subject.strip():
        raise ValueError("Token subject cannot be empty.")

    now = datetime.now(UTC)
    expires_at = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload = {
        "sub": subject,
        "type": "access",
        "iat": now,
        "exp": expires_at,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "jti": str(uuid4()),
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """Verify a JWT and return its claims."""

    if not token or not token.strip():
        raise InvalidTokenError("Invalid access token.")

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )

        if payload.get("type") != "access":
            raise InvalidTokenError("Invalid access token.")

        subject = payload.get("sub")

        if not isinstance(subject, str) or not subject.strip():
            raise InvalidTokenError("Invalid access token.")

        return payload

    except JWTError as exc:
        raise InvalidTokenError("Invalid access token.") from exc
