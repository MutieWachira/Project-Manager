"""Database-backed MFA login challenge creation and verification."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tokens import (
    InvalidTokenError,
    create_mfa_challenge_token,
    create_session_access_token,
    decode_mfa_challenge_token,
)
from app.models import MFALoginChallenge, User, UserMFA
from app.services.mfa import (
    MFAVerificationError,
    verify_totp_code,
)
from app.services.sessions import (
    CreatedSession,
    create_user_session,
)

CHALLENGE_EXPIRY_MINUTES = 5
MAX_FAILED_ATTEMPTS = 5


class MFAChallengeError(ValueError):
    """Raised when an MFA login challenge cannot be used."""


@dataclass(frozen=True)
class CreatedMFAChallenge:
    """A newly created challenge returned to the login client."""

    challenge_token: str
    expires_at: datetime


@dataclass(frozen=True)
class VerifiedMFAChallenge:
    """Authentication credentials issued after successful MFA."""

    access_token: str
    refresh_token: str
    client_type: str
    token_type: str
    expires_in: int
    session_id: UUID
    session_expires_at: datetime


def _as_utc(value: datetime) -> datetime:
    """Normalize database datetimes to timezone-aware UTC values."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def create_mfa_login_challenge(
    db: Session,
    user_id: UUID,
    *,
    client_type: str,
    now: datetime | None = None,
) -> CreatedMFAChallenge:
    """
    Create a short-lived challenge after successful password login.

    Older outstanding challenges for the same user are revoked.
    This service owns and commits its database transaction.
    """

    if client_type not in {"web", "mobile"}:
        raise MFAChallengeError("Unsupported client type.")

    current_time = now or datetime.now(UTC)

    try:
        user = db.scalar(select(User).where(User.id == user_id).with_for_update())

        if user is None or not user.is_active:
            raise MFAChallengeError("Account cannot complete login.")

        if user.email_verified_at is None:
            raise MFAChallengeError("Account cannot complete login.")

        mfa = db.scalar(
            select(UserMFA).where(UserMFA.user_id == user.id).with_for_update()
        )

        if mfa is None or not mfa.is_enabled or mfa.encrypted_secret is None:
            raise MFAChallengeError("MFA is not enabled.")

        outstanding_challenges = db.scalars(
            select(MFALoginChallenge)
            .where(
                MFALoginChallenge.user_id == user.id,
                MFALoginChallenge.consumed_at.is_(None),
                MFALoginChallenge.revoked_at.is_(None),
            )
            .with_for_update()
        ).all()

        for challenge in outstanding_challenges:
            challenge.revoked_at = current_time

        expires_at = current_time + timedelta(minutes=CHALLENGE_EXPIRY_MINUTES)

        challenge = MFALoginChallenge(
            user_id=user.id,
            created_at=current_time,
            expires_at=expires_at,
        )

        db.add(challenge)
        db.flush()

        challenge_token = create_mfa_challenge_token(
            subject=str(user.id),
            challenge_id=challenge.id,
            client_type=client_type,
            expires_delta=timedelta(minutes=CHALLENGE_EXPIRY_MINUTES),
        )

        db.commit()

        return CreatedMFAChallenge(
            challenge_token=challenge_token,
            expires_at=expires_at,
        )

    except Exception:
        db.rollback()
        raise


def verify_mfa_login_challenge(
    db: Session,
    challenge_token: str,
    code: str,
    *,
    device_name: str | None = None,
    user_agent: str | None = None,
    now: datetime | None = None,
) -> VerifiedMFAChallenge:
    """
    Verify a challenge and create an authenticated session.

    Invalid authenticator attempts are committed before an error is
    returned. Successful TOTP consumption, challenge consumption,
    and session creation are committed in one transaction.
    """

    try:
        payload = decode_mfa_challenge_token(challenge_token)

        user_id = UUID(payload["sub"])
        challenge_id = UUID(payload["jti"])
        client_type = payload["client_type"]

    except (InvalidTokenError, TypeError, ValueError, KeyError) as exc:
        raise MFAChallengeError("Invalid or expired MFA challenge.") from exc

    current_time = now or datetime.now(UTC)

    try:
        # Lock the user first. Challenge creation uses the same lock
        # order, helping prevent concurrent login operations.
        user = db.scalar(select(User).where(User.id == user_id).with_for_update())

        if user is None or not user.is_active:
            raise MFAChallengeError("MFA login is no longer available.")

        if user.email_verified_at is None:
            raise MFAChallengeError("MFA login is no longer available.")

        challenge = db.scalar(
            select(MFALoginChallenge)
            .where(
                MFALoginChallenge.id == challenge_id,
                MFALoginChallenge.user_id == user_id,
            )
            .with_for_update()
        )

        if challenge is None:
            raise MFAChallengeError("Invalid or expired MFA challenge.")

        if (
            challenge.consumed_at is not None
            or challenge.revoked_at is not None
            or _as_utc(challenge.expires_at) <= _as_utc(current_time)
        ):
            raise MFAChallengeError("Invalid or expired MFA challenge.")

        if challenge.failed_attempts >= MAX_FAILED_ATTEMPTS:
            challenge.revoked_at = current_time
            db.commit()
            raise MFAChallengeError("MFA challenge has been locked.")

        mfa = db.scalar(
            select(UserMFA).where(UserMFA.user_id == user_id).with_for_update()
        )

        if mfa is None or not mfa.is_enabled or mfa.encrypted_secret is None:
            challenge.revoked_at = current_time
            db.commit()
            raise MFAChallengeError("MFA login is no longer available.")

        try:
            verify_totp_code(
                db,
                user_id,
                code,
                now=current_time,
            )

        except MFAVerificationError as exc:
            if str(exc) == "Invalid authenticator code.":
                challenge.failed_attempts += 1

                if challenge.failed_attempts >= MAX_FAILED_ATTEMPTS:
                    challenge.revoked_at = current_time

                # Persist the failed attempt before returning an error.
                db.commit()

                if challenge.failed_attempts >= MAX_FAILED_ATTEMPTS:
                    raise MFAChallengeError("MFA challenge has been locked.") from exc

                raise MFAChallengeError("Invalid authenticator code.") from exc

            challenge.revoked_at = current_time
            db.commit()

            raise MFAChallengeError("MFA login is no longer available.") from exc

        challenge.consumed_at = current_time

        created_session: CreatedSession = create_user_session(
            db,
            user,
            client_type=client_type,
            device_name=device_name,
            user_agent=user_agent,
            commit=False,
        )

        access_token = create_session_access_token(
            subject=str(user.id),
            session_id=created_session.session_id,
        )

        result = VerifiedMFAChallenge(
            access_token=access_token,
            refresh_token=created_session.refresh_token,
            client_type=client_type,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            session_id=created_session.session_id,
            session_expires_at=created_session.expires_at,
        )

        # Atomically consume the challenge, consume the TOTP counter,
        # and persist the new session and refresh token.
        db.commit()

        return result

    except MFAChallengeError:
        if db.in_transaction():
            db.rollback()
        raise

    except Exception:
        db.rollback()
        raise
