"""TOTP-based multi-factor authentication enrollment and verification."""

from __future__ import annotations

import base64
import hmac
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import BytesIO
from uuid import UUID

import pyotp
import qrcode
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.encryption import decrypt_secret, encrypt_secret
from app.models import User, UserMFA

ENROLLMENT_EXPIRY_MINUTES = 10
TOTP_VALID_WINDOW = 1
TOTP_CODE_PATTERN = re.compile(r"^[0-9]{6}$")


class MFAEnrollmentError(ValueError):
    """Raised when MFA enrollment cannot be started or completed."""


class MFAVerificationError(ValueError):
    """Raised when an MFA verification attempt is invalid."""


@dataclass(frozen=True)
class MFAEnrollment:
    """Sensitive enrollment details returned to the authenticated user."""

    provisioning_uri: str
    qr_code_data_uri: str
    expires_at: datetime


@dataclass(frozen=True)
class MFAStatus:
    """Non-sensitive MFA status information."""

    enabled: bool
    confirmed_at: datetime | None


def _normalize_datetime(value: datetime) -> datetime:
    """Normalize a datetime to UTC for safe comparisons."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def _generate_qr_code_data_uri(provisioning_uri: str) -> str:
    """Generate an in-memory PNG QR code as a data URI."""

    image = qrcode.make(provisioning_uri)
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    encoded_image = base64.b64encode(buffer.getvalue()).decode("ascii")

    return f"data:image/png;base64,{encoded_image}"


def _find_matching_totp_counter(
    secret: str,
    code: str,
    *,
    now: datetime,
    last_counter: int | None,
) -> int | None:
    """
    Find a valid, unused TOTP counter.

    The accepted time window is one interval before or after the
    current interval. A previously accepted counter cannot be reused.
    """

    if not isinstance(code, str):
        return None

    if TOTP_CODE_PATTERN.fullmatch(code) is None:
        return None

    totp = pyotp.TOTP(secret, digits=6, interval=30)
    current_counter = totp.timecode(now)

    matching_counters = []

    for counter in range(
        max(0, current_counter - TOTP_VALID_WINDOW),
        current_counter + TOTP_VALID_WINDOW + 1,
    ):
        if last_counter is not None and counter <= last_counter:
            continue

        expected_code = totp.generate_otp(counter)

        if hmac.compare_digest(expected_code, code):
            matching_counters.append(counter)

    if not matching_counters:
        return None

    # Prefer the newest matching counter if a code happens to match
    # more than one interval.
    return max(matching_counters)


def begin_mfa_enrollment(
    db: Session,
    user: User,
    *,
    now: datetime | None = None,
) -> MFAEnrollment:
    """
    Start a new TOTP enrollment.

    The pending secret is encrypted before it is stored.
    The caller is responsible for committing or rolling back.
    """

    current_time = now or datetime.now(UTC)

    # Lock the user row to serialize simultaneous enrollment attempts,
    # including the case where no MFA record exists yet.
    locked_user = db.scalar(select(User).where(User.id == user.id).with_for_update())

    if locked_user is None:
        raise MFAEnrollmentError("User account was not found.")

    if not locked_user.is_active:
        raise MFAEnrollmentError("Inactive accounts cannot enroll MFA.")

    if locked_user.email_verified_at is None:
        raise MFAEnrollmentError("Email verification is required before enrolling MFA.")

    mfa = db.scalar(
        select(UserMFA).where(UserMFA.user_id == locked_user.id).with_for_update()
    )

    if mfa is not None and mfa.is_enabled:
        raise MFAEnrollmentError("MFA is already enabled.")

    secret = pyotp.random_base32()
    encrypted_secret = encrypt_secret(secret)
    expires_at = current_time + timedelta(minutes=ENROLLMENT_EXPIRY_MINUTES)

    if mfa is None:
        mfa = UserMFA(user_id=locked_user.id)
        db.add(mfa)

    mfa.pending_secret = encrypted_secret
    mfa.pending_expires_at = expires_at

    # Do not commit here. The API layer owns the transaction.
    db.flush()

    provisioning_uri = pyotp.TOTP(secret).provisioning_uri(
        name=locked_user.email,
        issuer_name=settings.APP_NAME,
    )

    return MFAEnrollment(
        provisioning_uri=provisioning_uri,
        qr_code_data_uri=_generate_qr_code_data_uri(provisioning_uri),
        expires_at=expires_at,
    )


def verify_mfa_enrollment(
    db: Session,
    user_id: UUID,
    code: str,
    *,
    now: datetime | None = None,
) -> bool:
    """
    Verify a pending enrollment and activate MFA.

    The accepted TOTP counter is stored to prevent code reuse.
    The caller is responsible for committing or rolling back.
    """

    current_time = now or datetime.now(UTC)

    mfa = db.scalar(select(UserMFA).where(UserMFA.user_id == user_id).with_for_update())

    if mfa is None or mfa.is_enabled:
        raise MFAEnrollmentError("No pending MFA enrollment is available.")

    if mfa.pending_secret is None or mfa.pending_expires_at is None:
        raise MFAEnrollmentError("No pending MFA enrollment is available.")

    if _normalize_datetime(mfa.pending_expires_at) <= _normalize_datetime(current_time):
        raise MFAEnrollmentError("MFA enrollment has expired. Start enrollment again.")

    try:
        secret = decrypt_secret(mfa.pending_secret)
    except ValueError as exc:
        raise MFAEnrollmentError(
            "Unable to verify the pending MFA enrollment."
        ) from exc

    matched_counter = _find_matching_totp_counter(
        secret,
        code,
        now=current_time,
        last_counter=mfa.last_totp_counter,
    )

    if matched_counter is None:
        raise MFAVerificationError("Invalid authenticator code.")

    mfa.encrypted_secret = mfa.pending_secret
    mfa.pending_secret = None
    mfa.pending_expires_at = None
    mfa.last_totp_counter = matched_counter
    mfa.is_enabled = True
    mfa.confirmed_at = current_time

    db.flush()

    return True


def verify_totp_code(
    db: Session,
    user_id: UUID,
    code: str,
    *,
    now: datetime | None = None,
) -> bool:
    """
    Verify a code against an enabled MFA configuration.

    This operation consumes the accepted TOTP counter.
    The caller is responsible for committing or rolling back.
    """

    current_time = now or datetime.now(UTC)

    mfa = db.scalar(select(UserMFA).where(UserMFA.user_id == user_id).with_for_update())

    if mfa is None or not mfa.is_enabled or mfa.encrypted_secret is None:
        raise MFAVerificationError("MFA is not enabled.")

    try:
        secret = decrypt_secret(mfa.encrypted_secret)
    except ValueError as exc:
        raise MFAVerificationError("Unable to verify the authenticator code.") from exc

    matched_counter = _find_matching_totp_counter(
        secret,
        code,
        now=current_time,
        last_counter=mfa.last_totp_counter,
    )

    if matched_counter is None:
        raise MFAVerificationError("Invalid authenticator code.")

    mfa.last_totp_counter = matched_counter

    db.flush()

    return True


def get_mfa_status(
    db: Session,
    user_id: UUID,
) -> MFAStatus:
    """Return MFA status without exposing any secret material."""

    mfa = db.scalar(select(UserMFA).where(UserMFA.user_id == user_id))

    if mfa is None:
        return MFAStatus(enabled=False, confirmed_at=None)

    return MFAStatus(
        enabled=mfa.is_enabled,
        confirmed_at=(
            _normalize_datetime(mfa.confirmed_at)
            if mfa.confirmed_at is not None
            else None
        ),
    )
