"""Reusable API dependencies."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tokens import (
    InvalidTokenError,
    decode_session_access_token,
)
from app.db.session import get_db
from app.models import User, UserSession


bearer_scheme = HTTPBearer(auto_error=False)


def _as_utc(value: datetime) -> datetime:
    """Normalize database datetimes to timezone-aware UTC values."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve a user only when their database-backed session is valid."""

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = decode_session_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
        session_id = UUID(payload["sid"])
    except (InvalidTokenError, ValueError, TypeError, KeyError):
        raise unauthorized from None

    user = db.scalar(select(User).where(User.id == user_id))

    if user is None or not user.is_active or user.email_verified_at is None:
        raise unauthorized

    authenticated_session = db.scalar(
        select(UserSession).where(
            UserSession.id == session_id,
            UserSession.user_id == user.id,
        )
    )

    if authenticated_session is None:
        raise unauthorized

    now = datetime.now(UTC)

    if authenticated_session.revoked_at is not None:
        raise unauthorized

    if _as_utc(authenticated_session.expires_at) <= now:
        raise unauthorized

    return user
