"""Secure refresh-token rotation and replay protection."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.refresh_tokens import (
    generate_refresh_token,
    hash_refresh_token,
)
from app.models import RefreshToken, UserSession


class InvalidRefreshTokenError(ValueError):
    """Raised when a refresh token cannot be used."""


class RefreshTokenReuseError(InvalidRefreshTokenError):
    """Raised when a previously consumed refresh token is reused."""


@dataclass(frozen=True)
class RotatedRefreshToken:
    """Contains the newly issued refresh-token credentials."""

    session_id: UUID
    user_id: UUID
    refresh_token: str
    client_type: str
    expires_at: datetime
    session_expires_at: datetime


def _as_utc(value: datetime) -> datetime:
    """Normalize database datetimes to timezone-aware UTC values."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def rotate_refresh_token(
    db: Session,
    raw_token: str,
    *,
    expected_client_type: str | None = None,
) -> RotatedRefreshToken:
    """
    Consume an existing refresh token and issue its replacement.

    The old token and new token are updated in one database
    transaction. PostgreSQL row-level locking prevents two
    requests from successfully consuming the same token.
    """

    if not isinstance(raw_token, str) or not raw_token:
        raise InvalidRefreshTokenError("Invalid refresh token.")

    token_hash = hash_refresh_token(raw_token)

    try:
        token_record = db.scalar(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .with_for_update()
        )

        if token_record is None:
            raise InvalidRefreshTokenError("Invalid refresh token.")

        session = db.scalar(
            select(UserSession)
            .where(UserSession.id == token_record.session_id)
            .with_for_update()
        )

        if session is None:
            raise InvalidRefreshTokenError("Invalid refresh token.")

        if expected_client_type is not None:
            if expected_client_type not in {"web", "mobile"}:
                raise InvalidRefreshTokenError("Invalid refresh token.")

            if session.client_type != expected_client_type:
                raise InvalidRefreshTokenError("Invalid refresh token.")

        now = datetime.now(UTC)

        if session.revoked_at is not None:
            raise InvalidRefreshTokenError("Invalid refresh token.")

        if _as_utc(session.expires_at) <= now:
            raise InvalidRefreshTokenError("Invalid refresh token.")

        if token_record.consumed_at is not None:
            # A consumed token has been presented again.
            # Revoke the entire session and all remaining tokens.
            session.revoked_at = now
            session.revoke_reason = "refresh_token_reuse"

            active_tokens = db.scalars(
                select(RefreshToken).where(
                    RefreshToken.session_id == session.id,
                    RefreshToken.revoked_at.is_(None),
                )
            ).all()

            for existing_token in active_tokens:
                existing_token.revoked_at = now

            db.commit()

            raise RefreshTokenReuseError(
                "Refresh token reuse detected. Session revoked."
            )

        if token_record.revoked_at is not None:
            raise InvalidRefreshTokenError("Invalid refresh token.")

        if _as_utc(token_record.expires_at) <= now:
            raise InvalidRefreshTokenError("Invalid refresh token.")

        user = session.user

        if not user.is_active or user.email_verified_at is None:
            session.revoked_at = now
            session.revoke_reason = "account_not_eligible"

            active_tokens = db.scalars(
                select(RefreshToken).where(
                    RefreshToken.session_id == session.id,
                    RefreshToken.revoked_at.is_(None),
                )
            ).all()

            for existing_token in active_tokens:
                existing_token.revoked_at = now

            db.commit()

            raise InvalidRefreshTokenError("This account cannot refresh its session.")

        new_expiry = min(
            _as_utc(session.expires_at),
            now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        new_raw_token = generate_refresh_token()

        replacement = RefreshToken(
            session_id=session.id,
            token_hash=hash_refresh_token(new_raw_token),
            expires_at=new_expiry,
        )

        # Mark the old token as consumed and link it to its replacement.
        token_record.consumed_at = now

        db.add(replacement)
        db.flush()

        token_record.replaced_by_id = replacement.id
        session.last_used_at = now

        result = RotatedRefreshToken(
            session_id=session.id,
            user_id=session.user_id,
            refresh_token=new_raw_token,
            client_type=session.client_type,
            expires_at=new_expiry,
            session_expires_at=_as_utc(session.expires_at),
        )

        db.commit()

        return result

    except (InvalidRefreshTokenError, RefreshTokenReuseError):
        # Preserve an intentional replay-detection revocation.
        if db.in_transaction():
            db.rollback()
        raise

    except Exception:
        db.rollback()
        raise
