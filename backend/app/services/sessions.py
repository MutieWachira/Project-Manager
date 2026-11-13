"""Database-backed authentication session management."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.refresh_tokens import (
    generate_refresh_token,
    hash_refresh_token,
)
from app.models import RefreshToken, User, UserSession


class SessionCreationError(ValueError):
    """Raised when an authentication session cannot be created."""


@dataclass(frozen=True)
class CreatedSession:
    """Credentials and metadata returned after session creation."""

    session_id: UUID
    refresh_token: str
    expires_at: datetime


def create_user_session(
    db: Session,
    user: User,
    *,
    client_type: str,
    device_name: str | None = None,
    user_agent: str | None = None,
    commit: bool = True,
) -> CreatedSession:
    """
    Create a session and its initial refresh token.

    The raw refresh token is returned to the caller but never stored
    in the database.

    When commit=False, the caller owns the transaction and must
    explicitly commit or roll it back.
    """

    if not user.is_active:
        raise SessionCreationError("Inactive users cannot create sessions.")

    if user.email_verified_at is None:
        raise SessionCreationError(
            "Email verification is required before creating a session."
        )

    if client_type not in {"web", "mobile"}:
        raise SessionCreationError("Unsupported client type.")

    if device_name is not None:
        device_name = device_name.strip() or None

        if device_name is not None and len(device_name) > 120:
            raise SessionCreationError("Device name is too long.")

    if user_agent is not None:
        user_agent = user_agent.strip() or None

        if user_agent is not None and len(user_agent) > 512:
            raise SessionCreationError("User agent is too long.")

    now = datetime.now(UTC)

    session_expires_at = now + timedelta(days=settings.SESSION_EXPIRE_DAYS)

    refresh_expires_at = min(
        session_expires_at,
        now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )

    raw_refresh_token = generate_refresh_token()

    session = UserSession(
        user_id=user.id,
        client_type=client_type,
        device_name=device_name,
        user_agent=user_agent,
        expires_at=session_expires_at,
    )

    refresh_token = RefreshToken(
        session=session,
        token_hash=hash_refresh_token(raw_refresh_token),
        expires_at=refresh_expires_at,
    )

    try:
        db.add(session)
        db.add(refresh_token)
        db.flush()

        result = CreatedSession(
            session_id=session.id,
            refresh_token=raw_refresh_token,
            expires_at=session_expires_at,
        )

        if commit:
            db.commit()

        return result

    except Exception:
        db.rollback()
        raise
