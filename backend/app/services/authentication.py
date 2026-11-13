"""Authentication and account registration services."""

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.email_delivery import (
    EmailDeliveryError,
    send_email_verification_email,
)
from app.services.email_verification import create_email_verification_token

logger = logging.getLogger(__name__)


def register_user(db: Session, registration: RegisterRequest) -> None:
    """
    Register an unverified user and send an email verification message.

    Existing email addresses receive the same public outcome as new
    registrations to reduce account enumeration.

    The database transaction is committed before email delivery.
    """

    normalized_email = registration.email.strip().casefold()

    # Hash the password before checking for an existing account.
    # This helps reduce timing differences between registration outcomes.
    password_hash = hash_password(registration.password)

    existing_user = db.scalar(select(User.id).where(User.email == normalized_email))

    if existing_user is not None:
        return

    user = User(
        full_name=registration.full_name,
        email=normalized_email,
        password_hash=password_hash,
        is_active=True,
    )

    try:
        db.add(user)
        db.flush()

        verification_token = create_email_verification_token(
            db,
            user,
        )

        db.commit()

    except IntegrityError:
        db.rollback()

        # Another request may have registered the same email between
        # our initial lookup and the database commit.
        existing_user = db.scalar(select(User.id).where(User.email == normalized_email))

        if existing_user is not None:
            return

        raise

    except Exception:
        db.rollback()
        raise

    # Send email only after the account and hashed token are committed.
    try:
        send_email_verification_email(
            recipient_email=user.email,
            recipient_name=user.full_name,
            token=verification_token,
        )

    except EmailDeliveryError:
        # Keep the account unverified. A resend workflow will allow
        # the user to request another verification message.
        logger.warning("Verification email delivery failed for a registered account.")


def authenticate_user(
    db: Session,
    credentials: LoginRequest,
) -> User | None:
    """
    Authenticate credentials and return the eligible user.

    Token and session creation are intentionally handled by the login
    route, which must determine whether MFA is required first.

    Return None for invalid credentials, inactive accounts,
    or accounts that have not verified their email.
    """

    normalized_email = credentials.email.strip().casefold()

    user = db.scalar(select(User).where(User.email == normalized_email))

    if user is None:
        # Perform a dummy password verification to reduce timing
        # differences between unknown and existing email addresses.
        verify_password(
            credentials.password,
            hash_password("Dummy-Password-For-Timing-2026"),
        )
        return None

    password_is_valid = verify_password(
        credentials.password,
        user.password_hash,
    )

    if not password_is_valid:
        return None

    if not user.is_active or user.email_verified_at is None:
        return None

    return user
