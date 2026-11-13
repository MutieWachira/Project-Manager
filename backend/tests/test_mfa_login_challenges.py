"""Tests for database-backed MFA login challenges."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pyotp
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.encryption import encrypt_secret
from app.core.refresh_tokens import hash_refresh_token
from app.core.tokens import (
    decode_mfa_challenge_token,
    decode_session_access_token,
)
from app.db.base import Base
from app.models import (
    MFALoginChallenge,
    RefreshToken,
    User,
    UserMFA,
    UserSession,
)
from app.services.mfa_login_challenges import (
    MFAChallengeError,
    create_mfa_login_challenge,
    verify_mfa_login_challenge,
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
def enabled_user(db_session):
    now = datetime.now(UTC)

    user = User(
        full_name="MFA Test User",
        email="mfa@example.com",
        password_hash="test-password-hash",
        is_active=True,
        email_verified_at=now,
    )

    secret = pyotp.random_base32()

    mfa = UserMFA(
        user=user,
        encrypted_secret=encrypt_secret(secret),
        is_enabled=True,
        confirmed_at=now,
    )

    db_session.add_all([user, mfa])
    db_session.commit()

    return user, secret


def test_create_mfa_login_challenge(
    db_session,
    enabled_user,
):
    user, _ = enabled_user
    now = datetime.now(UTC)

    result = create_mfa_login_challenge(
        db_session,
        user.id,
        client_type="web",
        now=now,
    )

    payload = decode_mfa_challenge_token(result.challenge_token)

    challenge = db_session.scalar(
        select(MFALoginChallenge).where(MFALoginChallenge.user_id == user.id)
    )

    assert challenge is not None
    assert challenge.id is not None
    assert challenge.consumed_at is None
    assert challenge.revoked_at is None
    assert challenge.failed_attempts == 0

    assert payload["sub"] == str(user.id)
    assert payload["jti"] == str(challenge.id)
    assert payload["client_type"] == "web"

    assert result.expires_at == now + timedelta(minutes=5)


def test_create_challenge_revokes_previous_outstanding_challenges(
    db_session,
    enabled_user,
):
    user, _ = enabled_user
    now = datetime.now(UTC)

    previous = MFALoginChallenge(
        user_id=user.id,
        created_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(minutes=4),
    )

    db_session.add(previous)
    db_session.commit()

    result = create_mfa_login_challenge(
        db_session,
        user.id,
        client_type="mobile",
        now=now,
    )

    db_session.refresh(previous)

    assert previous.revoked_at is not None
    assert previous.revoked_at.replace(tzinfo=UTC) == now

    new_payload = decode_mfa_challenge_token(result.challenge_token)

    assert new_payload["client_type"] == "mobile"
    assert new_payload["jti"] != str(previous.id)


def test_create_challenge_rejects_unsupported_client_type(
    db_session,
    enabled_user,
):
    user, _ = enabled_user

    with pytest.raises(MFAChallengeError):
        create_mfa_login_challenge(
            db_session,
            user.id,
            client_type="desktop",
        )

    assert db_session.scalar(select(MFALoginChallenge)) is None


def test_create_challenge_rejects_inactive_user(db_session):
    now = datetime.now(UTC)

    user = User(
        full_name="Inactive User",
        email="inactive@example.com",
        password_hash="test-password-hash",
        is_active=False,
        email_verified_at=now,
    )

    db_session.add(user)
    db_session.commit()

    with pytest.raises(MFAChallengeError):
        create_mfa_login_challenge(
            db_session,
            user.id,
            client_type="web",
        )

    assert db_session.scalar(select(MFALoginChallenge)) is None


def test_create_challenge_rejects_unverified_user(db_session):
    user = User(
        full_name="Unverified User",
        email="unverified@example.com",
        password_hash="test-password-hash",
        is_active=True,
        email_verified_at=None,
    )

    db_session.add(user)
    db_session.commit()

    with pytest.raises(MFAChallengeError):
        create_mfa_login_challenge(
            db_session,
            user.id,
            client_type="web",
        )

    assert db_session.scalar(select(MFALoginChallenge)) is None


def test_create_challenge_rejects_user_without_enabled_mfa(
    db_session,
    enabled_user,
):
    user, _ = enabled_user

    db_session.query(UserMFA).filter(UserMFA.user_id == user.id).delete()

    db_session.commit()

    with pytest.raises(MFAChallengeError):
        create_mfa_login_challenge(
            db_session,
            user.id,
            client_type="web",
        )


def test_successful_mfa_verification_creates_session(
    db_session,
    enabled_user,
):
    user, secret = enabled_user
    now = datetime.now(UTC)

    challenge_result = create_mfa_login_challenge(
        db_session,
        user.id,
        client_type="web",
        now=now,
    )

    code = pyotp.TOTP(secret).at(now)

    result = verify_mfa_login_challenge(
        db_session,
        challenge_result.challenge_token,
        code,
        device_name="Test Laptop",
        user_agent="Test Browser",
        now=now,
    )

    challenge = db_session.scalar(
        select(MFALoginChallenge).where(MFALoginChallenge.user_id == user.id)
    )

    session = db_session.scalar(
        select(UserSession).where(UserSession.id == result.session_id)
    )

    refresh_token = db_session.scalar(
        select(RefreshToken).where(RefreshToken.session_id == result.session_id)
    )

    access_payload = decode_session_access_token(result.access_token)

    assert challenge is not None
    assert challenge.consumed_at is not None
    assert challenge.revoked_at is None

    assert session is not None
    assert session.client_type == "web"
    assert session.device_name == "Test Laptop"
    assert session.user_agent == "Test Browser"

    assert refresh_token is not None
    assert refresh_token.token_hash == hash_refresh_token(result.refresh_token)
    assert refresh_token.token_hash != result.refresh_token

    assert access_payload["sub"] == str(user.id)
    assert access_payload["sid"] == str(result.session_id)

    assert result.token_type == "bearer"
    assert result.expires_in > 0
    assert result.session_expires_at == session.expires_at.replace(tzinfo=UTC)


def test_consumed_challenge_cannot_be_reused(
    db_session,
    enabled_user,
):
    user, secret = enabled_user
    now = datetime.now(UTC)

    challenge_result = create_mfa_login_challenge(
        db_session,
        user.id,
        client_type="web",
        now=now,
    )

    code = pyotp.TOTP(secret).at(now)

    verify_mfa_login_challenge(
        db_session,
        challenge_result.challenge_token,
        code,
        now=now,
    )

    with pytest.raises(MFAChallengeError):
        verify_mfa_login_challenge(
            db_session,
            challenge_result.challenge_token,
            code,
            now=now,
        )

    sessions = db_session.scalars(
        select(UserSession).where(UserSession.user_id == user.id)
    ).all()

    assert len(sessions) == 1


def test_invalid_codes_increment_failed_attempts(
    db_session,
    enabled_user,
):
    user, _ = enabled_user

    challenge_result = create_mfa_login_challenge(
        db_session,
        user.id,
        client_type="web",
    )

    for expected_attempt in range(1, 5):
        with pytest.raises(
            MFAChallengeError,
            match="Invalid authenticator code",
        ):
            verify_mfa_login_challenge(
                db_session,
                challenge_result.challenge_token,
                "abcdef",
            )

        challenge = db_session.scalar(
            select(MFALoginChallenge).where(MFALoginChallenge.user_id == user.id)
        )

        assert challenge is not None
        assert challenge.failed_attempts == expected_attempt
        assert challenge.revoked_at is None

    with pytest.raises(
        MFAChallengeError,
        match="locked",
    ):
        verify_mfa_login_challenge(
            db_session,
            challenge_result.challenge_token,
            "abcdef",
        )

    challenge = db_session.scalar(
        select(MFALoginChallenge).where(MFALoginChallenge.user_id == user.id)
    )

    assert challenge is not None
    assert challenge.failed_attempts == 5
    assert challenge.revoked_at is not None


def test_expired_challenge_is_rejected(
    db_session,
    enabled_user,
):
    user, _ = enabled_user

    expired_creation_time = datetime.now(UTC) - timedelta(minutes=6)

    challenge_result = create_mfa_login_challenge(
        db_session,
        user.id,
        client_type="web",
        now=expired_creation_time,
    )

    with pytest.raises(
        MFAChallengeError,
        match="Invalid or expired",
    ):
        verify_mfa_login_challenge(
            db_session,
            challenge_result.challenge_token,
            "abcdef",
        )

    assert db_session.scalar(select(UserSession)) is None


def test_revoked_challenge_is_rejected(
    db_session,
    enabled_user,
):
    user, _ = enabled_user

    challenge_result = create_mfa_login_challenge(
        db_session,
        user.id,
        client_type="web",
    )

    payload = decode_mfa_challenge_token(challenge_result.challenge_token)

    challenge = db_session.get(
        MFALoginChallenge,
        UUID(payload["jti"]),
    )

    assert challenge is not None

    challenge.revoked_at = datetime.now(UTC)
    db_session.commit()

    with pytest.raises(
        MFAChallengeError,
        match="Invalid or expired",
    ):
        verify_mfa_login_challenge(
            db_session,
            challenge_result.challenge_token,
            "abcdef",
        )

    assert db_session.scalar(select(UserSession)) is None
