"""Tests for TOTP-based MFA enrollment and verification."""

from datetime import UTC, datetime, timedelta
from urllib.parse import unquote

import pyotp
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.encryption import decrypt_secret, encrypt_secret
from app.db.base import Base
from app.models import User, UserMFA
from app.services.mfa import (
    MFAEnrollmentError,
    MFAVerificationError,
    begin_mfa_enrollment,
    get_mfa_status,
    verify_mfa_enrollment,
    verify_totp_code,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    test_session = sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
    )

    db = test_session()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def verified_user(db_session):
    user = User(
        full_name="Test Developer",
        email="developer@example.com",
        password_hash="test-password-hash",
        is_active=True,
        email_verified_at=datetime.now(UTC),
    )

    db_session.add(user)
    db_session.commit()

    return user


def test_begin_mfa_enrollment_creates_encrypted_pending_secret(
    db_session,
    verified_user,
):
    now = datetime(2026, 11, 12, 14, 0, 10, tzinfo=UTC)

    result = begin_mfa_enrollment(
        db_session,
        verified_user,
        now=now,
    )

    mfa = db_session.scalar(select(UserMFA).where(UserMFA.user_id == verified_user.id))

    assert mfa is not None
    assert mfa.pending_secret is not None
    assert mfa.encrypted_secret is None
    assert mfa.is_enabled is False

    decrypted_secret = decrypt_secret(mfa.pending_secret)

    assert decrypted_secret != mfa.pending_secret
    assert len(decrypted_secret) >= 16
    assert "otpauth://totp/" in result.provisioning_uri
    assert "developer@example.com" in unquote(result.provisioning_uri)
    assert result.qr_code_data_uri.startswith("data:image/png;base64,")
    assert result.expires_at == now + timedelta(minutes=10)


def test_begin_enrollment_does_not_commit_transaction(
    db_session,
    verified_user,
):
    begin_mfa_enrollment(db_session, verified_user)

    assert db_session.in_transaction()

    mfa = db_session.scalar(select(UserMFA).where(UserMFA.user_id == verified_user.id))

    assert mfa is not None

    db_session.rollback()

    assert db_session.scalar(select(UserMFA)) is None


def test_unverified_user_cannot_enroll_mfa(db_session):
    user = User(
        full_name="Unverified Developer",
        email="unverified@example.com",
        password_hash="test-password-hash",
        is_active=True,
        email_verified_at=None,
    )

    db_session.add(user)
    db_session.commit()

    with pytest.raises(MFAEnrollmentError):
        begin_mfa_enrollment(db_session, user)

    assert db_session.scalar(select(UserMFA)) is None


def test_inactive_user_cannot_enroll_mfa(db_session):
    user = User(
        full_name="Inactive Developer",
        email="inactive@example.com",
        password_hash="test-password-hash",
        is_active=False,
        email_verified_at=datetime.now(UTC),
    )

    db_session.add(user)
    db_session.commit()

    with pytest.raises(MFAEnrollmentError):
        begin_mfa_enrollment(db_session, user)

    assert db_session.scalar(select(UserMFA)) is None


def test_enabled_mfa_cannot_start_another_enrollment(
    db_session,
    verified_user,
):
    mfa = UserMFA(
        user_id=verified_user.id,
        encrypted_secret=encrypt_secret(pyotp.random_base32()),
        is_enabled=True,
        confirmed_at=datetime.now(UTC),
    )

    db_session.add(mfa)
    db_session.commit()

    with pytest.raises(MFAEnrollmentError):
        begin_mfa_enrollment(db_session, verified_user)


def test_verify_enrollment_activates_mfa(
    db_session,
    verified_user,
):
    now = datetime(2026, 11, 12, 14, 0, 10, tzinfo=UTC)

    begin_mfa_enrollment(
        db_session,
        verified_user,
        now=now,
    )

    mfa = db_session.scalar(select(UserMFA).where(UserMFA.user_id == verified_user.id))

    secret = decrypt_secret(mfa.pending_secret)
    code = pyotp.TOTP(secret).at(now)

    result = verify_mfa_enrollment(
        db_session,
        verified_user.id,
        code,
        now=now,
    )

    db_session.commit()

    assert result is True
    assert mfa.is_enabled is True
    assert mfa.encrypted_secret is not None
    assert decrypt_secret(mfa.encrypted_secret) == secret
    assert mfa.pending_secret is None
    assert mfa.pending_expires_at is None
    assert mfa.confirmed_at == now
    assert mfa.last_totp_counter is not None


def test_invalid_enrollment_code_does_not_activate_mfa(
    db_session,
    verified_user,
):
    begin_mfa_enrollment(db_session, verified_user)

    with pytest.raises(MFAVerificationError):
        verify_mfa_enrollment(
            db_session,
            verified_user.id,
            "000000",
        )

    mfa = db_session.scalar(select(UserMFA).where(UserMFA.user_id == verified_user.id))

    assert mfa.is_enabled is False
    assert mfa.pending_secret is not None


def test_expired_enrollment_is_rejected(
    db_session,
    verified_user,
):
    now = datetime(2026, 11, 12, 14, 0, 10, tzinfo=UTC)

    begin_mfa_enrollment(
        db_session,
        verified_user,
        now=now,
    )

    with pytest.raises(MFAEnrollmentError, match="expired"):
        verify_mfa_enrollment(
            db_session,
            verified_user.id,
            "123456",
            now=now + timedelta(minutes=11),
        )


def test_enrollment_code_cannot_be_reused(
    db_session,
    verified_user,
):
    now = datetime(2026, 11, 12, 14, 0, 10, tzinfo=UTC)

    begin_mfa_enrollment(
        db_session,
        verified_user,
        now=now,
    )

    mfa = db_session.scalar(select(UserMFA).where(UserMFA.user_id == verified_user.id))

    secret = decrypt_secret(mfa.pending_secret)
    code = pyotp.TOTP(secret).at(now)

    verify_mfa_enrollment(
        db_session,
        verified_user.id,
        code,
        now=now,
    )

    with pytest.raises(MFAVerificationError):
        verify_totp_code(
            db_session,
            verified_user.id,
            code,
            now=now,
        )


def test_active_totp_code_cannot_be_reused(
    db_session,
    verified_user,
):
    now = datetime(2026, 11, 12, 14, 0, 10, tzinfo=UTC)
    secret = pyotp.random_base32()

    mfa = UserMFA(
        user_id=verified_user.id,
        encrypted_secret=encrypt_secret(secret),
        is_enabled=True,
        confirmed_at=now,
    )

    db_session.add(mfa)
    db_session.commit()

    code = pyotp.TOTP(secret).at(now)

    assert verify_totp_code(
        db_session,
        verified_user.id,
        code,
        now=now,
    )

    db_session.commit()

    with pytest.raises(MFAVerificationError):
        verify_totp_code(
            db_session,
            verified_user.id,
            code,
            now=now,
        )


@pytest.mark.parametrize(
    "invalid_code",
    [
        "",
        "12345",
        "1234567",
        "abcdef",
        "１２３４５６",
        "123 456",
    ],
)
def test_invalid_code_formats_are_rejected(
    db_session,
    verified_user,
    invalid_code,
):
    now = datetime(2026, 11, 12, 14, 0, 10, tzinfo=UTC)
    secret = pyotp.random_base32()

    db_session.add(
        UserMFA(
            user_id=verified_user.id,
            encrypted_secret=encrypt_secret(secret),
            is_enabled=True,
            confirmed_at=now,
        )
    )
    db_session.commit()

    with pytest.raises(MFAVerificationError):
        verify_totp_code(
            db_session,
            verified_user.id,
            invalid_code,
            now=now,
        )


def test_totp_verification_requires_enabled_mfa(
    db_session,
    verified_user,
):
    with pytest.raises(MFAVerificationError, match="not enabled"):
        verify_totp_code(
            db_session,
            verified_user.id,
            "123456",
        )


def test_get_mfa_status_for_user_without_mfa(
    db_session,
    verified_user,
):
    status = get_mfa_status(db_session, verified_user.id)

    assert status.enabled is False
    assert status.confirmed_at is None


def test_get_mfa_status_for_enabled_user(
    db_session,
    verified_user,
):
    now = datetime.now(UTC)

    db_session.add(
        UserMFA(
            user_id=verified_user.id,
            encrypted_secret=encrypt_secret(pyotp.random_base32()),
            is_enabled=True,
            confirmed_at=now,
        )
    )
    db_session.commit()

    status = get_mfa_status(db_session, verified_user.id)

    assert status.enabled is True
    assert status.confirmed_at == now
    assert not hasattr(status, "encrypted_secret")
    assert not hasattr(status, "pending_secret")
