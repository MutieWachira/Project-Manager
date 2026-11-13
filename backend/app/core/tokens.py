"""JWT creation and validation for access and MFA challenge tokens."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from jose import JWTError, jwt

from app.core.config import settings


class InvalidTokenError(ValueError):
    """Raised when a token is invalid or cannot be verified."""


def _validate_subject(subject: str) -> None:
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("Token subject cannot be empty.")


def _encode_token(
    subject: str,
    *,
    token_type: str,
    expires_delta: timedelta,
    token_id: UUID | None = None,
    client_type: str | None = None,
    session_id: UUID | None = None,
) -> str:
    """Create a signed JWT with the application's standard claims."""

    _validate_subject(subject)

    now = datetime.now(UTC)

    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "jti": str(token_id or uuid4()),
    }

    if session_id is not None:
        payload["sid"] = str(session_id)

    if client_type is not None:
        payload["client_type"] = client_type

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(
    subject: str,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a transitional legacy access token."""

    return _encode_token(
        subject,
        token_type="access",
        expires_delta=(
            expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        ),
    )


def create_session_access_token(
    subject: str,
    *,
    session_id: UUID | str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create an access token bound to a database-backed session."""

    _validate_subject(subject)

    try:
        validated_session_id = UUID(str(session_id))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("Session ID must be a valid UUID.") from exc

    return _encode_token(
        subject,
        token_type="access",
        session_id=validated_session_id,
        expires_delta=(
            expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        ),
    )


def create_mfa_challenge_token(
    subject: str,
    *,
    challenge_id: UUID | str,
    client_type: str = "web",
    expires_delta: timedelta = timedelta(minutes=5),
) -> str:
    """Create a short-lived token that can only identify an MFA challenge."""
    if client_type not in {"web", "mobile"}:
        raise ValueError("Unsupported challenge client type.")

    _validate_subject(subject)

    if expires_delta.total_seconds() <= 0:
        raise ValueError("Challenge token expiry must be positive.")

    try:
        validated_challenge_id = UUID(str(challenge_id))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("Challenge ID must be a valid UUID.") from exc

    return _encode_token(
        subject,
        token_type="mfa_challenge",
        token_id=validated_challenge_id,
        client_type=client_type,
        expires_delta=expires_delta,
    )


def _decode_token(token: str, *, expected_type: str) -> dict:
    """Verify a JWT and enforce its expected token type."""

    if not isinstance(token, str) or not token.strip():
        raise InvalidTokenError("Invalid token.")

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )

        if payload.get("type") != expected_type:
            raise InvalidTokenError("Invalid token type.")

        subject = payload.get("sub")

        if not isinstance(subject, str) or not subject.strip():
            raise InvalidTokenError("Invalid token subject.")

        return payload

    except JWTError as exc:
        raise InvalidTokenError("Invalid token.") from exc


def decode_access_token(token: str) -> dict:
    """Verify a JWT access token."""

    return _decode_token(token, expected_type="access")


def decode_session_access_token(token: str) -> dict:
    """Verify an access token and require a valid session UUID."""

    payload = decode_access_token(token)

    try:
        UUID(payload.get("sid", ""))
    except (TypeError, ValueError, AttributeError) as exc:
        raise InvalidTokenError(
            "Access token is not bound to a valid session."
        ) from exc

    return payload


def decode_mfa_challenge_token(token: str) -> dict:
    """Verify an MFA challenge token and require a valid challenge UUID."""

    payload = _decode_token(token, expected_type="mfa_challenge")

    try:
        UUID(payload.get("jti", ""))
    except (TypeError, ValueError, AttributeError) as exc:
        raise InvalidTokenError("Invalid MFA challenge identifier.") from exc

    if payload.get("client_type") not in {"web", "mobile"}:
        raise InvalidTokenError("Invalid MFA challenge client type.")

    return payload
