from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EmailVerificationToken, User


DEFAULT_TOKEN_EXPIRY_MINUTES = 30


def generate_verification_token() -> str:
    """Generate a cryptographically secure, URL-safe verification token."""
    return secrets.token_urlsafe(32)


def hash_verification_token(token: str) -> str:
    """Return the SHA-256 hash of a verification token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _normalize_datetime(value: datetime) -> datetime:
    """Ensure datetimes can be compared consistently in UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def create_email_verification_token(
    db: Session,
    user: User,
    *,
    expiry_minutes: int = DEFAULT_TOKEN_EXPIRY_MINUTES,
    now: datetime | None = None,
) -> str:
    """
    Create a new verification token for a user.

    Existing unused tokens are invalidated.
    The caller is responsible for committing or rolling back the transaction.
    """
    if expiry_minutes <= 0:
        raise ValueError("Token expiry must be greater than zero minutes.")

    current_time = now or datetime.now(UTC)

    existing_tokens = db.scalars(
        select(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.consumed_at.is_(None),
        )
        .with_for_update()
    ).all()

    for existing_token in existing_tokens:
        existing_token.consumed_at = current_time

    raw_token = generate_verification_token()

    verification_record = EmailVerificationToken(
        user_id=user.id,
        token_hash=hash_verification_token(raw_token),
        expires_at=current_time + timedelta(minutes=expiry_minutes),
    )

    db.add(verification_record)
    db.flush()

    return raw_token


def verify_email_token(
    db: Session,
    raw_token: str,
    *,
    now: datetime | None = None,
) -> User | None:
    """
    Verify an email using a valid, unused token.

    Returns the verified user, or None when the token is invalid,
    expired, already consumed, or the account is already verified.

    The caller is responsible for committing or rolling back the transaction.
    """
    if not raw_token:
        return None

    current_time = now or datetime.now(UTC)
    token_hash = hash_verification_token(raw_token)

    verification_record = db.scalar(
        select(EmailVerificationToken)
        .where(EmailVerificationToken.token_hash == token_hash)
        .with_for_update()
    )

    if verification_record is None:
        return None

    if verification_record.consumed_at is not None:
        return None

    expiry_time = _normalize_datetime(verification_record.expires_at)
    comparison_time = _normalize_datetime(current_time)

    if expiry_time <= comparison_time:
        return None

    user = verification_record.user

    if user is None or user.email_verified_at is not None:
        return None

    verification_record.consumed_at = current_time
    user.email_verified_at = current_time

    db.flush()

    return user
